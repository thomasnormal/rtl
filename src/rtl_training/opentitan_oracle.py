from __future__ import annotations

from dataclasses import dataclass
import errno
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from .task_store import StoredTask


_REPO_COPY_IGNORE = shutil.ignore_patterns(
    ".git",
    "scratch",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
)
_RTL_EXTENSIONS = frozenset({".sv", ".v", ".svh", ".vh"})
_MODULE_DECL_RE = re.compile(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)\b")


@dataclass(frozen=True)
class OpenTitanDvsimOracle:
    cfg: str
    test: str
    tool: str
    golden_rtl_dir: Path
    repo_overlay_dir: Path | None
    overlay_rel_dir: str
    source_root: Path

    @classmethod
    def from_task(cls, task: StoredTask) -> "OpenTitanDvsimOracle":
        raw = task.metadata.get("oracle")
        if not isinstance(raw, dict) or raw.get("kind") != "opentitan_dvsim":
            raise ValueError(f"task {task.task_id} does not have an OpenTitan dvsim oracle")

        if task.shared_private_ref is not None:
            source_root = task.shared_private_ref.bundle_root()
        else:
            source_root_value = task.metadata.get("source", {}).get("source_root")
            if not source_root_value:
                raise ValueError(f"task {task.task_id} is missing source_root for OpenTitan oracle")
            source_root = Path(str(source_root_value)).resolve()

        return cls(
            cfg=str(raw["cfg"]),
            test=str(raw["test"]),
            tool=str(raw.get("tool", "xcelium")),
            golden_rtl_dir=task.root / "oracle" / str(raw["golden_rtl_dir"]),
            repo_overlay_dir=(
                task.root / "oracle" / str(raw["repo_overlay_dir"])
                if raw.get("repo_overlay_dir")
                else None
            ),
            overlay_rel_dir=str(raw["overlay_rel_dir"]),
            source_root=source_root,
        )


@dataclass(frozen=True)
class OpenTitanDvsimPlan:
    task: StoredTask
    oracle: OpenTitanDvsimOracle
    work_dir: Path
    repo_root: Path
    scratch_root: Path
    log_path: Path
    command: tuple[str, ...]


@dataclass(frozen=True)
class OpenTitanDvsimRunResult:
    plan: OpenTitanDvsimPlan
    returncode: int
    passed: bool
    stdout: str
    stderr: str


def build_opentitan_gold_selftest_plan(
    task: StoredTask,
    *,
    work_root: str | Path,
) -> OpenTitanDvsimPlan:
    oracle = OpenTitanDvsimOracle.from_task(task)

    work_dir, repo_root, overlay_dir = _prepare_repo_overlay(
        task,
        oracle,
        work_root=work_root,
        run_name="opentitan_gold_selftest",
        compat_mode="stub",
    )
    shutil.copytree(oracle.golden_rtl_dir, overlay_dir)
    return _finalize_dvsim_plan(task, oracle, work_dir, repo_root)


def build_opentitan_candidate_validation_plan(
    task: StoredTask,
    *,
    candidate_dir: str | Path,
    work_root: str | Path,
) -> OpenTitanDvsimPlan:
    oracle = OpenTitanDvsimOracle.from_task(task)
    work_dir, repo_root, overlay_dir = _prepare_repo_overlay(
        task,
        oracle,
        work_root=work_root,
        run_name="opentitan_candidate_validation",
        compat_mode="public",
    )
    shutil.copytree(oracle.golden_rtl_dir, overlay_dir)
    _stage_candidate_overlay(
        task,
        oracle=oracle,
        overlay_dir=overlay_dir,
        candidate_dir=Path(candidate_dir),
    )
    return _finalize_dvsim_plan(task, oracle, work_dir, repo_root)


def run_opentitan_dvsim_plan(
    plan: OpenTitanDvsimPlan,
    *,
    timeout_s: int = 1800,
) -> OpenTitanDvsimRunResult:
    completed = subprocess.run(
        plan.command,
        cwd=plan.repo_root,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    plan.log_path.write_text(completed.stdout + completed.stderr)
    return OpenTitanDvsimRunResult(
        plan=plan,
        returncode=completed.returncode,
        passed=completed.returncode == 0,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def validate_opentitan_gold_reference(
    task: StoredTask,
    *,
    work_root: str | Path,
    timeout_s: int = 1800,
) -> OpenTitanDvsimRunResult:
    plan = build_opentitan_gold_selftest_plan(task, work_root=work_root)
    return run_opentitan_dvsim_plan(plan, timeout_s=timeout_s)


def _copy_repo_tree(source_root: Path, destination_root: Path) -> None:
    shutil.copytree(
        source_root,
        destination_root,
        symlinks=True,
        copy_function=_link_or_copy_file,
        ignore=_REPO_COPY_IGNORE,
    )


def _link_or_copy_file(src: str, dst: str) -> None:
    try:
        os.link(src, dst)
    except OSError as err:
        if err.errno not in {errno.EXDEV, errno.EPERM, errno.ENOTSUP, errno.EACCES}:
            raise
        shutil.copy2(src, dst)


def _prepare_repo_overlay(
    task: StoredTask,
    oracle: OpenTitanDvsimOracle,
    *,
    work_root: str | Path,
    run_name: str,
    compat_mode: str,
) -> tuple[Path, Path, Path]:
    work_dir = Path(work_root).resolve() / task.dataset_name / task.task_id / run_name
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    repo_root = work_dir / "repo"
    _copy_repo_tree(oracle.source_root, repo_root)
    _stage_public_compat_abi(
        task,
        repo_root=repo_root,
        overlay_rel_dir=oracle.overlay_rel_dir,
        mode=compat_mode,
    )
    _stage_hidden_repo_overlay(oracle, repo_root)

    overlay_dir = repo_root / oracle.overlay_rel_dir
    overlay_dir.parent.mkdir(parents=True, exist_ok=True)
    if overlay_dir.exists():
        shutil.rmtree(overlay_dir)
    return work_dir, repo_root, overlay_dir


def _stage_hidden_repo_overlay(oracle: OpenTitanDvsimOracle, repo_root: Path) -> None:
    if oracle.repo_overlay_dir is None or not oracle.repo_overlay_dir.is_dir():
        return
    shutil.copytree(oracle.repo_overlay_dir, repo_root, dirs_exist_ok=True)


def _finalize_dvsim_plan(
    task: StoredTask,
    oracle: OpenTitanDvsimOracle,
    work_dir: Path,
    repo_root: Path,
) -> OpenTitanDvsimPlan:
    scratch_root = work_dir / "scratch"
    command = (
        sys.executable,
        "util/dvsim/dvsim.py",
        oracle.cfg,
        "-i",
        oracle.test,
        "-t",
        oracle.tool,
        "--proj-root",
        str(repo_root),
        "--scratch-root",
        str(scratch_root),
        "--purge",
        "--fixed-seed",
        "1",
        "--reseed",
        "1",
    )
    return OpenTitanDvsimPlan(
        task=task,
        oracle=oracle,
        work_dir=work_dir,
        repo_root=repo_root,
        scratch_root=scratch_root,
        log_path=work_dir / "dvsim.log",
        command=command,
    )


def _stage_public_compat_abi(
    task: StoredTask,
    *,
    repo_root: Path,
    overlay_rel_dir: str,
    mode: str,
) -> None:
    compat_source_dir = task.spec_dir / "compat"
    if not compat_source_dir.is_dir():
        return
    ip_root = (repo_root / overlay_rel_dir).parent
    compat_dest_dir = ip_root / "dv" / "compat"
    compat_dest_dir.mkdir(parents=True, exist_ok=True)
    for source_path in sorted(compat_source_dir.iterdir()):
        if source_path.is_file():
            destination = compat_dest_dir / source_path.name
            if source_path.suffix not in _RTL_EXTENSIONS:
                shutil.copy2(source_path, destination)
                continue
            if mode == "public":
                shutil.copy2(source_path, destination)
                continue
            if mode == "stub":
                destination.write_text(_render_compat_stub(source_path.read_text()))
                continue
            raise ValueError(f"unsupported compat staging mode {mode!r}")


def _stage_candidate_overlay(
    task: StoredTask,
    *,
    oracle: OpenTitanDvsimOracle,
    overlay_dir: Path,
    candidate_dir: Path,
) -> None:
    internal = _public_interface_internal(task)
    native_interface = dict(internal["native_interface"])
    projection = dict(internal["projection"])
    top_module = str(native_interface["top_module"])
    candidate_files = tuple(
        sorted(
            (
                path
                for path in candidate_dir.iterdir()
                if path.is_file() and path.suffix in _RTL_EXTENSIONS
            ),
            key=lambda path: path.name,
        )
    )
    if not candidate_files:
        raise ValueError(f"candidate directory {candidate_dir} does not contain any RTL files")
    top_source = _find_candidate_top_source(candidate_files, top_module)

    support_files = [str(item) for item in projection.get("support_files", ())]
    support_texts: list[tuple[str, str]] = []
    for support_file in support_files:
        source_path = task.spec_dir / "interface" / support_file
        if not source_path.is_file():
            raise FileNotFoundError(f"missing public support file for wrapper: {source_path}")
        shutil.copy2(source_path, overlay_dir / support_file)
        support_texts.append((support_file, source_path.read_text()))

    compat_files = tuple(
        sorted(
            path.name
            for path in (task.spec_dir / "compat").iterdir()
            if path.is_file() and path.suffix in _RTL_EXTENSIONS
        )
    ) if (task.spec_dir / "compat").is_dir() else ()

    removable_includes = {
        support_file for support_file in support_files
    } | {
        f"task/spec/interface/{support_file}" for support_file in support_files
    } | {
        compat_file for compat_file in compat_files
    } | {
        f"task/spec/compat/{compat_file}" for compat_file in compat_files
    } | {
        candidate_file.name for candidate_file in candidate_files
    } | {
        f"submission/{candidate_file.name}" for candidate_file in candidate_files
    } | {
        f"candidate/{top_module}_candidate{top_source.suffix}"
    }

    candidate_overlay_dir = overlay_dir / "candidate"
    candidate_overlay_dir.mkdir(parents=True, exist_ok=True)
    candidate_units: list[tuple[str, str]] = []
    for candidate_file in candidate_files:
        if candidate_file == top_source:
            renamed = candidate_overlay_dir / f"{top_module}_candidate{candidate_file.suffix}"
            renamed_text = _rewrite_first_module_name(
                candidate_file.read_text(),
                old_name=top_module,
                new_name=f"{top_module}_candidate",
            )
            renamed.write_text(renamed_text)
            candidate_units.append(
                (
                    renamed.name,
                    _strip_known_include_lines(renamed_text, removable_includes),
                )
            )
            continue
        destination = candidate_overlay_dir / candidate_file.name
        shutil.copy2(candidate_file, destination)
        candidate_units.append(
            (
                destination.name,
                _strip_known_include_lines(candidate_file.read_text(), removable_includes),
            )
        )

    wrapper_source = oracle.source_root / oracle.overlay_rel_dir / f"{top_module}.sv"
    if not wrapper_source.is_file():
        wrapper_source = oracle.golden_rtl_dir / f"{top_module}.sv"
    wrapper_text = _render_candidate_wrapper(
        source_text=wrapper_source.read_text(),
        top_module=top_module,
        projection_ports=tuple(projection.get("ports", ())),
        support_units=tuple(support_texts),
        candidate_units=tuple(candidate_units),
    )
    (overlay_dir / f"{top_module}.sv").write_text(wrapper_text)


def _public_interface_internal(task: StoredTask) -> dict[str, object]:
    source = task.metadata.get("source", {})
    if not isinstance(source, dict):
        raise ValueError(f"task {task.task_id} is missing source metadata")
    internal = source.get("public_interface_internal")
    if not isinstance(internal, dict):
        raise ValueError(f"task {task.task_id} is missing public_interface_internal metadata")
    return internal


def _find_candidate_top_source(candidate_files: tuple[Path, ...], top_module: str) -> Path:
    pattern = re.compile(rf"\bmodule\s+{re.escape(top_module)}\b")
    for candidate_file in candidate_files:
        if pattern.search(candidate_file.read_text()):
            return candidate_file
    raise ValueError(f"unable to find top module {top_module!r} in candidate RTL bundle")


def _rewrite_first_module_name(text: str, *, old_name: str, new_name: str) -> str:
    pattern = re.compile(rf"(\bmodule\s+){re.escape(old_name)}(\b)")
    rewritten, count = pattern.subn(rf"\1{new_name}\2", text, count=1)
    if count != 1:
        raise ValueError(f"unable to rewrite module name {old_name} -> {new_name}")
    return rewritten


def _render_candidate_wrapper(
    *,
    source_text: str,
    top_module: str,
    projection_ports: tuple[dict[str, object], ...],
    support_units: tuple[tuple[str, str], ...],
    candidate_units: tuple[tuple[str, str], ...],
) -> str:
    preamble, header = _extract_module_preamble_and_header(source_text, top_module)
    lines: list[str] = []
    stripped_preamble = preamble.rstrip()
    if stripped_preamble:
        lines.append(stripped_preamble)
        lines.append("")
    lines.append("// Generated wrapper adapting the public task ABI to the native OpenTitan oracle ABI.")
    for name, text in support_units:
        lines.append(f"// Begin inlined public support unit: {name}")
        lines.append(text.rstrip())
        lines.append(f"// End inlined public support unit: {name}")
        lines.append("")
    for name, text in candidate_units:
        lines.append(f"// Begin inlined candidate unit: {name}")
        lines.append(text.rstrip())
        lines.append(f"// End inlined candidate unit: {name}")
        lines.append("")
    lines.append(header.rstrip())
    lines.append("")

    cast_aliases: dict[str, tuple[str, str]] = {}
    for port in projection_ports:
        if not bool(port["cast_required"]):
            continue
        name = str(port["name"])
        native_alias = f"native_cast_{name}_t"
        public_alias = f"public_cast_{name}_t"
        cast_aliases[name] = (native_alias, public_alias)
        lines.append(f"  typedef {port['native_type']} {native_alias};")
        lines.append(f"  typedef {port['public_type']} {public_alias};")
    if cast_aliases:
        lines.append("")

    for port in projection_ports:
        name = str(port["name"])
        _, public_alias = cast_aliases.get(name, ("", ""))
        signal_type = public_alias or _render_sv_signal_type(str(port["public_type"]))
        lines.append(f"  {signal_type} candidate_{port['name']};")
    if projection_ports:
        lines.append("")

    for port in projection_ports:
        direction = str(port["direction"])
        name = str(port["name"])
        public_type = str(port["public_type"])
        native_type = str(port["native_type"])
        cast_required = bool(port["cast_required"])
        native_alias, public_alias = cast_aliases.get(name, ("", ""))
        if direction == "input":
            rhs = name if not cast_required else f"{public_alias}'({name})"
            lines.append(f"  assign candidate_{name} = {rhs};")
        elif direction == "output":
            rhs = f"candidate_{name}" if not cast_required else f"{native_alias}'(candidate_{name})"
            lines.append(f"  assign {name} = {rhs};")
        elif direction == "inout":
            raise NotImplementedError("inout candidate wrapper ports are not supported yet")
        else:
            raise ValueError(f"unsupported port direction {direction!r}")
    if projection_ports:
        lines.append("")

    lines.append(f"  {top_module}_candidate u_candidate (")
    for index, port in enumerate(projection_ports):
        suffix = "," if index < len(projection_ports) - 1 else ""
        lines.append(f"    .{port['name']}(candidate_{port['name']}){suffix}")
    lines.append("  );")
    lines.append("endmodule")
    lines.append("")
    return "\n".join(lines)


def _strip_known_include_lines(text: str, removable_includes: set[str]) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        match = re.match(r'^\s*`include\s+"([^"]+)"\s*$', line)
        if match is None:
            lines.append(line)
            continue
        include_target = match.group(1)
        if include_target in removable_includes or Path(include_target).name in removable_includes:
            lines.append(f"// stripped include during oracle staging: {include_target}")
            continue
        lines.append(line)
    stripped = "\n".join(lines)
    if text.endswith("\n"):
        return stripped + "\n"
    return stripped


def _extract_module_preamble_and_header(source_text: str, top_module: str) -> tuple[str, str]:
    match = re.search(rf"\bmodule\s+{re.escape(top_module)}\b", source_text)
    if match is None:
        raise ValueError(f"unable to find module header for {top_module!r}")
    start = match.start()
    preamble = source_text[:start]
    index = match.end()
    length = len(source_text)

    def skip_ws(pos: int) -> int:
        while pos < length and source_text[pos].isspace():
            pos += 1
        return pos

    def consume_balanced_parens(pos: int) -> int:
        if pos >= length or source_text[pos] != "(":
            raise ValueError(f"expected '(' while parsing module header for {top_module!r}")
        depth = 1
        pos += 1
        while pos < length and depth > 0:
            char = source_text[pos]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            pos += 1
        if depth != 0:
            raise ValueError(f"unterminated parenthesis while parsing module header for {top_module!r}")
        return pos

    while True:
        index = skip_ws(index)
        if source_text.startswith("import", index):
            semicolon = source_text.find(";", index)
            if semicolon == -1:
                raise ValueError(f"unterminated import clause while parsing module header for {top_module!r}")
            index = semicolon + 1
            continue
        break

    index = skip_ws(index)
    if index < length and source_text[index] == "#":
        index += 1
        index = skip_ws(index)
        index = consume_balanced_parens(index)

    index = skip_ws(index)
    if index < length and source_text[index] == "(":
        index = consume_balanced_parens(index)
        index = skip_ws(index)

    semicolon = source_text.find(";", index)
    if semicolon == -1:
        raise ValueError(f"unable to locate end of module header for {top_module!r}")
    return preamble, source_text[start:semicolon + 1]


def _render_sv_signal_type(type_expr: str) -> str:
    stripped = type_expr.strip()
    if not stripped:
        return "logic"
    if stripped.startswith("["):
        return f"logic {stripped}"
    if stripped.startswith("signed [") or stripped.startswith("unsigned ["):
        return f"logic {stripped}"
    return stripped


def _render_compat_stub(source_text: str) -> str:
    match = re.search(r"^\s*(module|interface|package)\s+([A-Za-z_][A-Za-z0-9_$]*)", source_text, re.MULTILINE)
    if match is None:
        raise ValueError("unable to derive compat stub declaration")
    kind = match.group(1)
    name = match.group(2)
    if kind == "module":
        return f"module {name}; endmodule : {name}\n"
    if kind == "interface":
        return f"interface {name}; endinterface : {name}\n"
    return f"package {name}; endpackage : {name}\n"
