from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping

from .interface_contracts import discover_public_interface_spec, read_public_top_module


_MICRO_ARCH_INTERFACE_PATTERNS = ("*_micro_arch_if.sv",)
_MICRO_ARCH_BIND_PATTERNS = ("*_micro_arch_bind.sv",)
_MODULE_DECL_RE = re.compile(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)\b")


@dataclass(frozen=True)
class MicroArchInterfaceSpec:
    interface_name: str
    instance_name: str
    signals: tuple[str, ...]
    dut_outputs: tuple[str, ...]
    dut_inputs: tuple[str, ...]
    dut_inouts: tuple[str, ...]
    modports: tuple[str, ...]
    source_path: Path


def find_micro_arch_dir(spec_dir: Path) -> Path | None:
    candidate = spec_dir / "micro_arch"
    if candidate.is_dir():
        return candidate
    return None


def discover_micro_arch_interface_spec(spec_dir: Path) -> MicroArchInterfaceSpec | None:
    micro_arch_dir = find_micro_arch_dir(spec_dir)
    if micro_arch_dir is None:
        return None
    interface_files: list[Path] = []
    for pattern in _MICRO_ARCH_INTERFACE_PATTERNS:
        interface_files.extend(sorted(micro_arch_dir.glob(pattern)))
    unique_files = tuple(dict.fromkeys(interface_files))
    if len(unique_files) != 1:
        return None
    return parse_micro_arch_interface_spec(unique_files[0])


def parse_micro_arch_interface_spec(source_path: str | Path) -> MicroArchInterfaceSpec:
    path = Path(source_path)
    source_text = path.read_text()
    interface_match = re.search(
        r"\binterface\s+([A-Za-z_][A-Za-z0-9_$]*)\b",
        source_text,
    )
    if interface_match is None:
        raise ValueError(f"unable to find interface declaration in {path}")
    interface_name = interface_match.group(1)
    signal_names = _parse_logic_signal_names(source_text)
    modports = _parse_modports(source_text)
    dut_modport = modports.get("dut")
    if dut_modport is None:
        raise ValueError(f"micro_arch interface {path} must define a `dut` modport")
    if not {"tb", "mon"} & modports.keys():
        raise ValueError(
            f"micro_arch interface {path} must define at least one `tb` or `mon` modport"
        )
    for direction_names in modports.values():
        for names in direction_names.values():
            for signal in names:
                if signal not in signal_names:
                    raise ValueError(
                        f"micro_arch interface {path} modport references unknown signal {signal!r}"
                    )
    return MicroArchInterfaceSpec(
        interface_name=interface_name,
        instance_name=f"u_{interface_name}",
        signals=tuple(signal_names),
        dut_outputs=tuple(dut_modport.get("output", ())),
        dut_inputs=tuple(dut_modport.get("input", ())),
        dut_inouts=tuple(dut_modport.get("inout", ())),
        modports=tuple(sorted(modports)),
        source_path=path,
    )


def validate_public_micro_arch_dir(spec_dir: str | Path) -> MicroArchInterfaceSpec | None:
    spec_root = Path(spec_dir)
    micro_arch_dir = find_micro_arch_dir(spec_root)
    if micro_arch_dir is None:
        return None
    readme_path = micro_arch_dir / "README.md"
    if not readme_path.is_file():
        raise ValueError(f"micro_arch contract {micro_arch_dir} must include README.md")
    return discover_micro_arch_interface_spec(spec_root)


def discover_micro_arch_bind_module(spec_dir: str | Path) -> tuple[str, Path] | None:
    spec_root = Path(spec_dir)
    micro_arch_dir = find_micro_arch_dir(spec_root)
    if micro_arch_dir is None:
        return None
    bind_files: list[Path] = []
    for pattern in _MICRO_ARCH_BIND_PATTERNS:
        bind_files.extend(sorted(micro_arch_dir.glob(pattern)))
    unique_files = tuple(dict.fromkeys(bind_files))
    if len(unique_files) != 1:
        return None
    bind_path = unique_files[0]
    module_match = _MODULE_DECL_RE.search(bind_path.read_text())
    if module_match is None:
        raise ValueError(f"unable to find bind-module declaration in {bind_path}")
    return module_match.group(1), bind_path


def write_micro_arch_bind_check_tb(
    task_dir: str | Path,
    output_path: str | Path,
) -> Path | None:
    task_root = Path(task_dir)
    spec_dir = task_root / "spec"
    bind_module = discover_micro_arch_bind_module(spec_dir)
    if bind_module is None:
        return None
    public_interface = discover_public_interface_spec(spec_dir)
    if public_interface is None:
        raise ValueError(f"public task {task_root} does not define a public interface contract")
    top_module = read_public_top_module(task_root / "task.json")

    bind_module_name, _ = bind_module
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        _render_micro_arch_bind_check_tb(
            top_module=top_module,
            ports=list(public_interface.ports),
            bind_module_name=bind_module_name,
        )
    )
    return output


def _parse_logic_signal_names(source_text: str) -> tuple[str, ...]:
    names: list[str] = []
    declaration_pattern = re.compile(
        r"^\s*logic(?:\s+\[[^\]]+\])?\s+([^;]+);",
        re.MULTILINE,
    )
    for match in declaration_pattern.finditer(source_text):
        declaration = match.group(1)
        for raw_name in declaration.split(","):
            name = raw_name.strip()
            if not name:
                continue
            signal_match = re.match(r"([A-Za-z_][A-Za-z0-9_$]*)$", name)
            if signal_match is None:
                raise ValueError(f"unsupported logic declaration fragment {name!r}")
            names.append(signal_match.group(1))
    return tuple(names)


def _parse_modports(source_text: str) -> dict[str, dict[str, tuple[str, ...]]]:
    modports: dict[str, dict[str, tuple[str, ...]]] = {}
    modport_pattern = re.compile(
        r"\bmodport\s+([A-Za-z_][A-Za-z0-9_$]*)\s*\((.*?)\)\s*;",
        re.DOTALL,
    )
    for match in modport_pattern.finditer(source_text):
        modport_name = match.group(1)
        body = match.group(2)
        direction_map: dict[str, list[str]] = {"input": [], "output": [], "inout": []}
        normalized = " ".join(body.replace("\n", " ").split())
        for entry in re.finditer(
            r"\b(input|output|inout)\b\s+([^()]+?)(?=(?:\binput\b|\boutput\b|\binout\b|$))",
            normalized,
        ):
            direction = entry.group(1)
            for raw_name in entry.group(2).split(","):
                name = raw_name.strip()
                if not name:
                    continue
                signal_match = re.match(r"([A-Za-z_][A-Za-z0-9_$]*)$", name)
                if signal_match is None:
                    raise ValueError(
                        f"unsupported modport signal fragment {name!r} in {modport_name}"
                    )
                direction_map[direction].append(signal_match.group(1))
        modports[modport_name] = {
            direction: tuple(names)
            for direction, names in direction_map.items()
            if names
        }
    return modports


def _render_micro_arch_bind_check_tb(
    *,
    top_module: str,
    ports: list[Any],
    bind_module_name: str,
) -> str:
    lines = ["module tb_bind_check;"]
    for raw_port in ports:
        if not isinstance(raw_port, Mapping):
            raise ValueError("public interface port entries must be objects")
        lines.append(f"  {_render_tb_signal_decl(raw_port)}")
    lines.extend(
        [
            "",
            f"  {top_module} dut (",
        ]
    )
    port_lines = [f"    .{raw_port['name']}({raw_port['name']})" for raw_port in ports]
    if port_lines:
        lines.append(",\n".join(port_lines))
    lines.extend(
        [
            "  );",
            "",
            f"  {bind_module_name} u_bind();",
            "endmodule",
            "",
        ]
    )
    return "\n".join(lines)


def _render_tb_signal_decl(raw_port: Mapping[str, Any]) -> str:
    name = str(raw_port["name"])
    width = str(raw_port.get("width", "logic")).strip()
    if not width or width == "logic":
        return f"logic {name};"
    if width.startswith("["):
        return f"logic {width} {name};"
    return f"{width} {name};"
