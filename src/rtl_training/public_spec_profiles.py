from __future__ import annotations

from pathlib import Path
import re
from typing import Any


_MARKDOWN_LINK_RE = re.compile(r"!?\[([^\]]+)\]\(([^)]+)\)")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_FENCED_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)

_DROP_MARKDOWN_LINE_PATTERNS = (
    "reports.opentitan.org",
    "dashboards.lowrisc.org",
    "Comportable guideline",
    "conforms to the",
    "See that document for integration overview",
    "top level system.",
    "Additional features such as",
    "Design & verification stage",
    "HW development stages",
    "Simulation results",
    "$REPO_TOP",
    "util/regtool",
    "util/dvsim",
    "dvsim.py",
    "regtool.py",
    "cip_lib",
    "github.com/lowRISC/opentitan",
    "Device Interface Functions",
    "Chromium EC",
    "hw/ip/",
    "hw/dv/",
)

_DROP_HJSON_LINE_PATTERNS = (
    "Copyright lowRISC contributors",
    "OpenTitan project",
)

_DROP_HJSON_KEYS = {
    "cip_id",
    "design_spec",
    "dv_doc",
    "hw_checklist",
    "sw_checklist",
    "revisions",
    "commit_id",
    "dif_stage",
    "life_stage",
    "design_stage",
    "verification_stage",
}

_TEXT_REPLACEMENTS = (
    ("OpenTitan-style", "reference-derived"),
    ("OpenTitan DV environment", "reference verification environment"),
    ("OpenTitan tests", "reference-derived tests"),
    ("OpenTitan peripherals", "supported peripherals"),
    ("OpenTitan peripheral", "target peripheral"),
    ("OpenTitan system-on-chip (SoC)", "target system-on-chip (SoC)"),
    ("OpenTitan system", "target system"),
    ("OpenTitan reset and power manager blocks", "system reset and power-management logic"),
    ("OpenTitan reset and power manager", "system reset and power manager"),
    ("OpenTitan internal memory", "trusted internal memory"),
    ("OpenTitan memory", "trusted internal memory"),
    ("OpenTitan secure perimeter", "trusted security boundary"),
    ("OpenTitan-internal", "trusted-internal"),
    ("OpenTitan internal", "trusted internal"),
    ("OpenTitan", "target device"),
    ("TileLink Uncached Lightweight (TL-UL)", "control-bus request/response"),
    ("TileLink Uncached Light (TL-UL)", "control-bus request/response"),
    ("TileLink Uncached Light", "control bus"),
    ("TileLink", "control bus"),
    ("TL-UL", "control bus"),
    ("Ibex core", "main processor"),
    ("Ibex", "main processor"),
    ("RACL", "register access control"),
)

_CONTROL_PATH_PATTERNS = (
    "doc/checklist.md",
    "data/BUILD",
)

_DROP_DATA_FILE_PATTERNS = (
    "*testplan*.hjson",
    "*.hjson.tpl",
)

_DROP_DV_FILE_PATTERNS = (
    "*_sim_cfg.hjson",
)


def apply_public_spec_profile(
    spec_dir: str | Path,
    *,
    profile: str,
    task_id: str,
    top_module: str,
    public_interface: dict[str, Any] | None,
    oracle_metadata: dict[str, Any] | None,
) -> None:
    spec_root = Path(spec_dir)
    if profile == "opentitan_task_facing_v1":
        _apply_opentitan_task_facing_profile(
            spec_root,
            task_id=task_id,
            top_module=top_module,
            public_interface=public_interface,
            oracle_metadata=oracle_metadata,
        )
        return
    raise ValueError(f"unsupported public spec profile {profile!r}")


def _apply_opentitan_task_facing_profile(
    spec_dir: Path,
    *,
    task_id: str,
    top_module: str,
    public_interface: dict[str, Any] | None,
    oracle_metadata: dict[str, Any] | None,
) -> None:
    _drop_irrelevant_public_files(spec_dir)
    _sanitize_public_markdown_tree(spec_dir)
    _sanitize_public_hjson_tree(spec_dir)
    if public_interface is not None:
        _write_public_interface_markdown(spec_dir, top_module=top_module, public_interface=public_interface)
    _write_public_dv_readme(spec_dir, task_id=task_id, top_module=top_module, oracle_metadata=oracle_metadata)
    _prepend_public_readme_note(spec_dir, top_module=top_module)


def _drop_irrelevant_public_files(spec_dir: Path) -> None:
    for relative in _CONTROL_PATH_PATTERNS:
        candidate = spec_dir / relative
        if candidate.exists():
            candidate.unlink()

    data_dir = spec_dir / "data"
    if data_dir.is_dir():
        for pattern in _DROP_DATA_FILE_PATTERNS:
            for path in data_dir.glob(pattern):
                if path.is_file():
                    path.unlink()

    dv_dir = spec_dir / "dv"
    if dv_dir.is_dir():
        for pattern in _DROP_DV_FILE_PATTERNS:
            for path in dv_dir.glob(pattern):
                if path.is_file():
                    path.unlink()


def _sanitize_public_markdown_tree(spec_dir: Path) -> None:
    for path in sorted(spec_dir.rglob("*.md")):
        path.write_text(_sanitize_markdown_text(path.read_text(), path.relative_to(spec_dir)))


def _sanitize_public_hjson_tree(spec_dir: Path) -> None:
    for path in sorted(spec_dir.rglob("*.hjson")):
        path.write_text(_sanitize_hjson_text(path.read_text()))


def _sanitize_markdown_text(text: str, relative_path: Path) -> str:
    text = _HTML_COMMENT_RE.sub("", text)
    text = _replace_markdown_links(text)
    text = _FENCED_BLOCK_RE.sub(_sanitize_fenced_block, text)

    kept_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            kept_lines.append("")
            continue
        line = line.replace(" This module", "")
        if any(pattern in line for pattern in _DROP_MARKDOWN_LINE_PATTERNS):
            continue
        if re.fullmatch(r"`?[A-Za-z0-9_]+`?:", line.strip()):
            continue
        if line.strip() == "## Compatibility":
            continue
        if line.strip() == "This module":
            continue
        if re.search(r"\b[a-z0-9_]+_pkg::", line):
            continue
        if re.search(r"\bprim_[A-Za-z0-9_]+\b", line):
            continue
        kept_lines.append(line)

    text = "\n".join(kept_lines)
    for before, after in _TEXT_REPLACEMENTS:
        text = text.replace(before, after)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"

    if relative_path == Path("README.md"):
        text = _rewrite_top_level_heading(text)
    return text


def _sanitize_fenced_block(match: re.Match[str]) -> str:
    block = match.group(0)
    if any(pattern in block for pattern in ("$REPO_TOP", "dvsim.py", "regtool.py", "util/dvsim", "util/regtool")):
        return ""
    return block


def _replace_markdown_links(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        label = match.group(1)
        if match.group(0).startswith("!"):
            return ""
        return label

    return _MARKDOWN_LINK_RE.sub(repl, text)


def _rewrite_top_level_heading(text: str) -> str:
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if line.startswith("# "):
            heading = re.sub(r"\s+HWIP Technical Specification$", " Specification", line[2:].strip())
            heading = re.sub(r"\s*\([^)]*\)\s*$", "", heading)
            lines[idx] = f"# {heading}"
            break
    return "\n".join(lines).strip() + "\n"


def _sanitize_hjson_text(text: str) -> str:
    kept_lines: list[str] = []
    skip_block_depth = 0
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if skip_block_depth > 0:
            skip_block_depth += raw_line.count("{") + raw_line.count("[")
            skip_block_depth -= raw_line.count("}") + raw_line.count("]")
            continue
        if any(pattern in raw_line for pattern in _DROP_HJSON_LINE_PATTERNS):
            continue
        key_match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", raw_line)
        if key_match is not None and key_match.group(1) in _DROP_HJSON_KEYS:
            skip_block_depth = raw_line.count("{") + raw_line.count("[")
            skip_block_depth -= raw_line.count("}") + raw_line.count("]")
            if skip_block_depth <= 0:
                skip_block_depth = 0
            continue
        line = raw_line
        for before, after in _TEXT_REPLACEMENTS:
            line = line.replace(before, after)
        kept_lines.append(line.rstrip())
    return "\n".join(kept_lines).strip() + "\n"


def _write_public_interface_markdown(
    spec_dir: Path,
    *,
    top_module: str,
    public_interface: dict[str, Any],
) -> None:
    doc_dir = spec_dir / "doc"
    doc_dir.mkdir(parents=True, exist_ok=True)
    interface_path = doc_dir / "interfaces.md"
    support_files = sorted(path.name for path in (spec_dir / "interface").glob("*.sv"))

    lines = [
        "# Interface Summary",
        "",
        f"The canonical machine-readable interface for `{top_module}` is defined in `spec/interface/`.",
        "Use the SystemVerilog files there as the source of truth for port directions, packed types, parameters, and modports.",
        "",
    ]
    parameters = list(public_interface.get("parameters", ()))
    if parameters:
        lines.extend([
            "## Parameters",
            "",
            "| Name | Default |",
            "| --- | --- |",
        ])
        for parameter in parameters:
            lines.append(
                f"| `{parameter['name']}` | `{parameter.get('value', '')}` |"
            )
        lines.append("")

    ports = list(public_interface.get("ports", ()))
    if ports:
        lines.extend([
            "## Ports",
            "",
            "| Direction | Name | Type |",
            "| --- | --- | --- |",
        ])
        for port in ports:
            port_type = port.get("width", "logic")
            lines.append(f"| `{port['direction']}` | `{port['name']}` | `{port_type}` |")
        lines.append("")

    notes = list(public_interface.get("notes", ()))
    if notes:
        lines.extend(["## Notes", ""])
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    if support_files:
        lines.extend([
            "## Supporting SV Files",
            "",
        ])
        for name in support_files:
            lines.append(f"- `spec/interface/{name}`")
        lines.append("")

    interface_path.write_text("\n".join(lines).rstrip() + "\n")


def _write_public_dv_readme(
    spec_dir: Path,
    *,
    task_id: str,
    top_module: str,
    oracle_metadata: dict[str, Any] | None,
) -> None:
    dv_dir = spec_dir / "dv"
    if not dv_dir.exists() and oracle_metadata is None:
        return
    dv_dir.mkdir(parents=True, exist_ok=True)
    test_name = None if oracle_metadata is None else oracle_metadata.get("test")
    tool = None if oracle_metadata is None else oracle_metadata.get("tool")
    kind = None if oracle_metadata is None else oracle_metadata.get("kind")
    has_micro_arch = (spec_dir / "micro_arch").is_dir()

    lines = [
        f"# {top_module} Verification Notes",
        "",
        "This directory describes the public verification intent for the task.",
        "It is not a build recipe for the hidden oracle and it intentionally avoids upstream repo-specific setup details.",
        "",
        "## Public Guidance",
        "",
        f"- Implement the behavior described in `spec/README.md`, `spec/doc/`, and the canonical SV boundary in `spec/interface/` for `{top_module}`.",
    ]
    if has_micro_arch:
        lines.append("- If `spec/micro_arch/` is present, instantiate the required microarchitecture interface exactly and drive its documented observation signals.")
    if kind is not None:
        lines.append(f"- The hidden oracle is a reference-backed simulation environment (`{kind}`) derived from a stronger verification bench.")
    if tool is not None:
        lines.append(f"- The hidden oracle runs under `{tool}`.")
    if test_name is not None:
        lines.append(f"- A smoke-style hidden validation target exists for this task (`{test_name}`).")
    lines.extend([
        "",
        "## What This Means For A Solver",
        "",
        "- Focus on documented reset behavior, register-visible side effects, interrupt/alert behavior, and the externally visible protocol behavior.",
        "- Do not rely on hidden repo files or hidden package imports; the public task bundle is the intended implementation boundary.",
        "",
    ])
    dv_readme = dv_dir / "README.md"
    dv_readme.write_text("\n".join(lines).rstrip() + "\n")


def _prepend_public_readme_note(spec_dir: Path, *, top_module: str) -> None:
    readme_path = spec_dir / "README.md"
    if not readme_path.exists():
        return
    text = readme_path.read_text()
    note = (
        "This task is presented as a standalone hardware-design problem. "
        f"Use `spec/interface/` as the canonical boundary for `{top_module}`, "
        "and use `spec/micro_arch/` only when deeper verification compatibility is required.\n\n"
    )
    lines = text.splitlines()
    if len(lines) >= 1 and lines[0].startswith("# "):
        body = "\n".join([lines[0], "", note.rstrip(), *lines[1:]]).strip() + "\n"
    else:
        body = note + text
    readme_path.write_text(body)
