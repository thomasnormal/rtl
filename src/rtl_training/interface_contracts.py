from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Any, Mapping


_PORT_DIRECTIONS = frozenset({"input", "output", "inout"})
_SV_IDENT_DECL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")
_SV_IDENT_RE = re.compile(r"(?<!')\b[A-Za-z_][A-Za-z0-9_$]*\b")
_SV_KEYWORDS = frozenset(
    {
        "logic",
        "bit",
        "wire",
        "reg",
        "signed",
        "unsigned",
        "int",
        "shortint",
        "longint",
        "integer",
        "parameter",
        "localparam",
        "default",
        "package",
        "endpackage",
    }
)
_ARRAY_TYPE_RE = re.compile(r"^(?P<base>[A-Za-z_][A-Za-z0-9_:]*)(?P<dims>(?:\s*\[[^\]]+\])*)$")
_PACKED_DIM_RE = re.compile(r"\[([^\]:]+):([^\]]+)\]")
_REPLICATION_RE = re.compile(r"^\{\s*(\d+)\s*\{\s*([^{}]+?)\s*\}\s*\}$")
_REG_PKG_PARAM_RE = re.compile(
    r"\bparameter\s+(?:int(?:\s+unsigned)?\s+)?(?P<name>NumAlerts|NumRegs)\s*=\s*(?P<value>[^;]+);"
)
_PUBLIC_INTERFACE_PATTERNS = ("*_public_if.sv",)
_SV_TOP_MODULE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")

_OPENTITAN_SELF_CONTAINED_PROFILE = "opentitan_self_contained_v1"
_OPENTITAN_OPAQUE_TYPE_WIDTHS = {
    "ast_pkg::adc_ast_req_t": 3,
    "ast_pkg::adc_ast_rsp_t": 11,
    "dma_pkg::lsio_trigger_t": 11,
    "dma_pkg::sys_req_t": 184,
    "dma_pkg::sys_rsp_t": 40,
    "lc_ctrl_pkg::lc_tx_t": 4,
    "prim_alert_pkg::alert_rx_t": 4,
    "prim_alert_pkg::alert_tx_t": 2,
    "prim_mubi_pkg::mubi4_t": 4,
    "prim_ram_1p_pkg::ram_1p_cfg_rsp_t": 1,
    "prim_ram_1p_pkg::ram_1p_cfg_t": 12,
    "spi_device_pkg::passthrough_req_t": 13,
    "spi_device_pkg::passthrough_rsp_t": 4,
    "tlul_pkg::tl_d2h_t": 66,
    "tlul_pkg::tl_h2d_t": 109,
    "top_racl_pkg::racl_error_log_t": 37,
    "top_racl_pkg::racl_policy_vec_t": 4,
}


@dataclass(frozen=True)
class MaterializedPublicInterfaceSv:
    interface_dir: Path
    readme_path: Path
    sv_path: Path
    support_paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class PreparedPublicInterfaceContract:
    interface: dict[str, Any]
    support_files: tuple[tuple[str, str], ...] = ()
    hidden_metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class PublicInterfaceSpec:
    interface_name: str
    ports: tuple[dict[str, str], ...]
    source_path: Path


def read_public_top_module(public_task_path: str | Path) -> str:
    payload = json.loads(Path(public_task_path).read_text())
    top_module = str(payload.get("top_module", "")).strip()
    if not _SV_TOP_MODULE_NAME_RE.fullmatch(top_module):
        raise ValueError(f"invalid public top module name in {public_task_path}: {top_module!r}")
    return top_module


def discover_public_interface_spec(spec_dir: str | Path) -> PublicInterfaceSpec | None:
    interface_dir = Path(spec_dir) / "interface"
    if not interface_dir.is_dir():
        return None
    interface_files: list[Path] = []
    for pattern in _PUBLIC_INTERFACE_PATTERNS:
        interface_files.extend(sorted(interface_dir.glob(pattern)))
    unique_files = tuple(dict.fromkeys(interface_files))
    if len(unique_files) != 1:
        return None
    return parse_public_interface_spec(unique_files[0])


def parse_public_interface_spec(source_path: str | Path) -> PublicInterfaceSpec:
    path = Path(source_path)
    source_text = path.read_text()
    interface_match = re.search(
        r"^\s*interface\s+([A-Za-z_][A-Za-z0-9_$]*)\b",
        source_text,
        re.MULTILINE,
    )
    if interface_match is None:
        raise ValueError(f"unable to find interface declaration in {path}")
    declarations = _parse_public_signal_declarations(source_text)
    if not declarations:
        raise ValueError(f"public interface {path} does not declare any signals")
    modports = _parse_public_modports(source_text)
    dut_modport = modports.get("dut")
    if dut_modport is None:
        raise ValueError(f"public interface {path} must define a `dut` modport")
    ports: list[dict[str, str]] = []
    for signal_name, signal_type in declarations:
        signal_direction = dut_modport.get(signal_name)
        if signal_direction is None:
            continue
        port = {
            "name": signal_name,
            "direction": signal_direction,
        }
        normalized_width = _normalize_parsed_public_signal_type(signal_type)
        if normalized_width is not None:
            port["width"] = normalized_width
        ports.append(port)
    if not ports:
        raise ValueError(f"public interface {path} `dut` modport does not reference any signals")
    return PublicInterfaceSpec(
        interface_name=interface_match.group(1),
        ports=tuple(ports),
        source_path=path,
    )


def normalize_public_interface_contract(
    raw_interface: Mapping[str, Any],
    *,
    candidate_top_module: str,
) -> dict[str, Any]:
    top_module = str(raw_interface.get("top_module", candidate_top_module))
    if top_module != candidate_top_module:
        raise ValueError(
            f"public interface top module {top_module!r} does not match "
            f"candidate top module {candidate_top_module!r}"
        )

    declared_module_name = str(raw_interface.get("declared_module_name", top_module))
    parameters = _normalize_parameters(raw_interface.get("parameters", []))
    ports = _normalize_ports_from_interface(raw_interface)
    modports = _normalize_modports(raw_interface.get("modports"), ports)

    normalized: dict[str, Any] = {
        "top_module": top_module,
        "declared_module_name": declared_module_name,
        "parameters": parameters,
        "ports": ports,
        "inputs": _normalize_direction_group(raw_interface.get("inputs"), "input", ports),
        "outputs": _normalize_direction_group(raw_interface.get("outputs"), "output", ports),
        "modports": modports,
    }

    inouts = _normalize_direction_group(raw_interface.get("inouts"), "inout", ports)
    if inouts:
        normalized["inouts"] = inouts

    notes = raw_interface.get("notes")
    if notes is not None:
        if not isinstance(notes, list):
            raise ValueError("public interface notes must be a list")
        normalized["notes"] = [str(note) for note in notes]

    return normalized


def materialize_public_interface_sv(
    spec_dir: str | Path,
    interface: Mapping[str, Any],
    *,
    support_files: tuple[tuple[str, str], ...] = (),
) -> MaterializedPublicInterfaceSv:
    spec_dir_path = Path(spec_dir)
    interface_dir = spec_dir_path / "interface"
    interface_dir.mkdir(parents=True, exist_ok=True)

    top_module = str(interface["top_module"])
    interface_name = f"{top_module}_public_if"
    sv_path = interface_dir / f"{interface_name}.sv"
    readme_path = interface_dir / "README.md"
    support_paths: list[Path] = []
    for filename, content in support_files:
        support_path = interface_dir / filename
        support_path.write_text(content)
        support_paths.append(support_path)

    sv_path.write_text(
        _render_public_interface_sv(
            interface_name,
            interface,
            include_files=tuple(filename for filename, _ in support_files),
        )
    )
    readme_path.write_text(
        _render_interface_readme(
            interface_name,
            sv_path.name,
            tuple(filename for filename, _ in support_files),
        )
    )

    return MaterializedPublicInterfaceSv(
        interface_dir=interface_dir,
        readme_path=readme_path,
        sv_path=sv_path,
        support_paths=tuple(support_paths),
    )


def prepare_public_interface_contract(
    raw_interface: Mapping[str, Any],
    *,
    candidate_top_module: str,
    profile: str | None = None,
    task_id: str | None = None,
    source_root: str | Path | None = None,
) -> PreparedPublicInterfaceContract:
    normalized = normalize_public_interface_contract(
        raw_interface,
        candidate_top_module=candidate_top_module,
    )
    if profile is None:
        return PreparedPublicInterfaceContract(interface=normalized)
    if profile != _OPENTITAN_SELF_CONTAINED_PROFILE:
        raise ValueError(f"unsupported public interface profile {profile!r}")
    if task_id is None:
        raise ValueError("OpenTitan public interface projection requires task_id")
    return _prepare_opentitan_self_contained_contract(
        normalized,
        task_id=task_id,
        source_root=None if source_root is None else Path(source_root),
    )


def _normalize_parameters(raw_parameters: Any) -> list[dict[str, str]]:
    if not isinstance(raw_parameters, list):
        raise ValueError("public interface parameters must be a list")
    parameters: list[dict[str, str]] = []
    for raw_parameter in raw_parameters:
        if not isinstance(raw_parameter, Mapping) or "name" not in raw_parameter:
            raise ValueError("public interface parameter entries must be objects with a name")
        parameter: dict[str, str] = {"name": str(raw_parameter["name"])}
        if raw_parameter.get("value") is not None:
            parameter["value"] = str(raw_parameter["value"])
        parameters.append(parameter)
    return parameters


def _normalize_ports_from_interface(raw_interface: Mapping[str, Any]) -> list[dict[str, str]]:
    raw_ports = raw_interface.get("ports")
    if raw_ports:
        return _normalize_ports(raw_ports)

    derived_ports: list[dict[str, str]] = []
    for direction_key, direction in (
        ("inputs", "input"),
        ("outputs", "output"),
        ("inouts", "inout"),
    ):
        raw_group = raw_interface.get(direction_key, [])
        if raw_group in (None, []):
            continue
        if not isinstance(raw_group, list):
            raise ValueError(f"public interface {direction_key} must be a list")
        for raw_entry in raw_group:
            if not isinstance(raw_entry, Mapping) or "name" not in raw_entry:
                raise ValueError(f"public interface {direction_key} entries must have a name")
            port = {"name": str(raw_entry["name"]), "direction": direction}
            if raw_entry.get("width") not in {None, ""}:
                port["width"] = str(raw_entry["width"])
            if raw_entry.get("description") not in {None, ""}:
                port["description"] = str(raw_entry["description"])
            derived_ports.append(port)
    return derived_ports


def _normalize_ports(raw_ports: Any) -> list[dict[str, str]]:
    if not isinstance(raw_ports, list):
        raise ValueError("public interface ports must be a list")
    ports: list[dict[str, str]] = []
    for raw_port in raw_ports:
        if not isinstance(raw_port, Mapping) or "name" not in raw_port or "direction" not in raw_port:
            raise ValueError("public interface ports must contain name and direction")
        direction = str(raw_port["direction"]).lower()
        if direction not in _PORT_DIRECTIONS:
            raise ValueError(f"invalid public interface direction {direction!r}")
        port = {
            "name": str(raw_port["name"]),
            "direction": direction,
        }
        if raw_port.get("width") not in {None, ""}:
            port["width"] = str(raw_port["width"])
        if raw_port.get("description") not in {None, ""}:
            port["description"] = str(raw_port["description"])
        ports.append(port)
    return ports


def _normalize_direction_group(
    raw_group: Any,
    direction: str,
    ports: list[dict[str, str]],
) -> list[dict[str, str]]:
    if raw_group is None:
        return [dict(port) for port in ports if port["direction"] == direction]
    if not isinstance(raw_group, list):
        raise ValueError(f"public interface {direction}s must be a list")
    normalized: list[dict[str, str]] = []
    for raw_entry in raw_group:
        if not isinstance(raw_entry, Mapping) or "name" not in raw_entry:
            raise ValueError(f"public interface {direction}s entries must have a name")
        entry = {str(key): str(value) for key, value in raw_entry.items() if value is not None}
        normalized.append(entry)
    return normalized


def _normalize_modports(raw_modports: Any, ports: list[dict[str, str]]) -> list[dict[str, Any]]:
    if raw_modports is None:
        return _default_modports(ports)
    if not isinstance(raw_modports, list):
        raise ValueError("public interface modports must be a list")

    known_port_names = {port["name"] for port in ports}
    modports: list[dict[str, Any]] = []
    for raw_modport in raw_modports:
        if not isinstance(raw_modport, Mapping) or "name" not in raw_modport:
            raise ValueError("public interface modport entries must have a name")
        raw_signals = raw_modport.get("signals")
        if not isinstance(raw_signals, list):
            raise ValueError("public interface modport signals must be a list")
        signals: list[dict[str, str]] = []
        for raw_signal in raw_signals:
            if not isinstance(raw_signal, Mapping) or "name" not in raw_signal or "direction" not in raw_signal:
                raise ValueError("public interface modport signals must have name and direction")
            signal_name = str(raw_signal["name"])
            if signal_name not in known_port_names:
                raise ValueError(f"public interface modport references unknown port {signal_name!r}")
            direction = str(raw_signal["direction"]).lower()
            if direction not in _PORT_DIRECTIONS:
                raise ValueError(f"invalid modport direction {direction!r}")
            signals.append({"name": signal_name, "direction": direction})
        modports.append({"name": str(raw_modport["name"]), "signals": signals})
    return modports


def _default_modports(ports: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {
            "name": "dut",
            "signals": [
                {"name": port["name"], "direction": port["direction"]}
                for port in ports
            ],
        },
        {
            "name": "tb",
            "signals": [
                {"name": port["name"], "direction": _reverse_direction(port["direction"])}
                for port in ports
            ],
        },
    ]


def _reverse_direction(direction: str) -> str:
    if direction == "input":
        return "output"
    if direction == "output":
        return "input"
    return direction


def _render_public_interface_sv(
    interface_name: str,
    interface: Mapping[str, Any],
    *,
    include_files: tuple[str, ...] = (),
) -> str:
    parameters = interface.get("parameters", [])
    ports = interface.get("ports", [])
    modports = interface.get("modports", [])

    lines: list[str] = [
        "// Generated from the public task interface contract.",
        "// This is the machine-checkable SV form of the public DUT boundary.",
    ]
    if include_files:
        lines.append("")
        for include_file in include_files:
            lines.append(f"`include \"{include_file}\"")

    if parameters:
        lines.append(f"interface {interface_name} #(")
        for index, parameter in enumerate(parameters):
            suffix = "," if index < len(parameters) - 1 else ""
            if parameter.get("value") is None:
                lines.append(f"  parameter {parameter['name']}{suffix}")
            else:
                lines.append(f"  parameter {parameter['name']} = {parameter['value']}{suffix}")
        lines.append(");")
    else:
        lines.append(f"interface {interface_name};")

    if ports:
        lines.append("")
        for port in ports:
            declaration = _render_signal_declaration(port)
            if port.get("description"):
                lines.append(f"  {declaration} // {port['description']}")
            else:
                lines.append(f"  {declaration}")

    for modport in modports:
        lines.append("")
        lines.append(f"  modport {modport['name']} (")
        for index, signal in enumerate(modport["signals"]):
            suffix = "," if index < len(modport["signals"]) - 1 else ""
            lines.append(f"    {signal['direction']} {signal['name']}{suffix}")
        lines.append("  );")

    lines.append("endinterface")
    lines.append("")
    return "\n".join(lines)


def _render_signal_declaration(port: Mapping[str, Any]) -> str:
    signal_type = _port_signal_type(port)
    return f"{signal_type} {port['name']};"


def _port_signal_type(port: Mapping[str, Any]) -> str:
    raw_width = str(port.get("width", "")).strip()
    if not raw_width:
        return "logic"
    if raw_width.startswith("["):
        return f"logic {raw_width}"
    if raw_width.startswith("signed [") or raw_width.startswith("unsigned ["):
        return f"logic {raw_width}"
    return raw_width


def _render_interface_readme(
    interface_name: str,
    sv_filename: str,
    support_files: tuple[str, ...],
) -> str:
    lines = [
        "# Public SV Interface Contract",
        "",
        "This directory is generated from the public task interface contract and provides the",
        "public DUT boundary as SystemVerilog artifacts.",
        "",
        f"- `{sv_filename}` defines `{interface_name}` with canonical `dut` and `tb` modports.",
    ]
    for support_file in support_files:
        lines.append(f"- `{support_file}` provides self-contained public SV support types for the task.")
    lines.extend(
        [
            "- These files describe the public boundary only. Hidden oracles and deep-DV",
            "  microarchitecture ABIs live elsewhere.",
        ]
    )
    if support_files:
        lines.append("- The generated support files remove the need to import upstream repository packages.")
    else:
        lines.extend(
            [
                "- Package-qualified types are preserved verbatim from the task metadata, so",
                "  compiling these files may require additional package definitions from the task spec.",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def _parse_public_signal_declarations(source_text: str) -> tuple[tuple[str, str], ...]:
    declarations: list[tuple[str, str]] = []
    for raw_line in source_text.splitlines():
        line = raw_line.split("//", 1)[0].strip()
        if not line or line.startswith("`") or " modport " in f" {line} ":
            continue
        if line.startswith(("interface ", "endinterface", "package ", "endpackage")):
            continue
        if line.startswith("parameter "):
            continue
        if not line.endswith(";"):
            continue
        line = line[:-1].strip()
        if not line:
            continue
        tokens = line.split()
        if len(tokens) < 2:
            continue
        signal_name = tokens[-1]
        if not _SV_IDENT_DECL_RE.fullmatch(signal_name):
            continue
        signal_type = " ".join(tokens[:-1]).strip()
        if not signal_type:
            continue
        declarations.append((signal_name, signal_type))
    return tuple(declarations)


def _normalize_parsed_public_signal_type(signal_type: str) -> str | None:
    normalized = signal_type.strip()
    if normalized == "logic":
        return None
    if normalized.startswith("logic "):
        return normalized[len("logic ") :].strip()
    return normalized


def _parse_public_modports(source_text: str) -> dict[str, dict[str, str]]:
    modports: dict[str, dict[str, str]] = {}
    modport_pattern = re.compile(
        r"\bmodport\s+([A-Za-z_][A-Za-z0-9_$]*)\s*\((.*?)\)\s*;",
        re.DOTALL,
    )
    for match in modport_pattern.finditer(source_text):
        modport_name = match.group(1)
        body = " ".join(match.group(2).replace("\n", " ").split())
        direction_map: dict[str, str] = {}
        for entry in re.finditer(
            r"\b(input|output|inout)\b\s+([^()]+?)(?=(?:\binput\b|\boutput\b|\binout\b|$))",
            body,
        ):
            direction = entry.group(1)
            for raw_name in entry.group(2).split(","):
                signal_name = raw_name.strip()
                if not signal_name:
                    continue
                if not _SV_IDENT_DECL_RE.fullmatch(signal_name):
                    raise ValueError(
                        f"unsupported modport signal fragment {signal_name!r} in {modport_name}"
                    )
                direction_map[signal_name] = direction
        modports[modport_name] = direction_map
    return modports


def _prepare_opentitan_self_contained_contract(
    normalized: Mapping[str, Any],
    *,
    task_id: str,
    source_root: Path | None,
) -> PreparedPublicInterfaceContract:
    implicit_params = _resolve_opentitan_implicit_parameters(task_id, source_root)
    native_interface = deepcopy(dict(normalized))
    projected_parameters = _project_opentitan_parameters(
        normalized.get("parameters", []),
        implicit_params=implicit_params,
    )
    projected_ports, projection = _project_opentitan_ports(
        normalized.get("ports", []),
        task_id=str(normalized["top_module"]),
        parameter_names=tuple(parameter["name"] for parameter in projected_parameters),
        implicit_params=implicit_params,
    )
    projected_interface = {
        "top_module": str(normalized["top_module"]),
        "declared_module_name": str(normalized["declared_module_name"]),
        "parameters": projected_parameters,
        "ports": projected_ports,
        "inputs": [dict(port) for port in projected_ports if port["direction"] == "input"],
        "outputs": [dict(port) for port in projected_ports if port["direction"] == "output"],
        "modports": deepcopy(list(normalized.get("modports", []))),
    }
    if normalized.get("inouts"):
        projected_interface["inouts"] = [
            dict(port) for port in projected_ports if port["direction"] == "inout"
        ]
    if normalized.get("notes") is not None:
        projected_interface["notes"] = list(normalized["notes"])

    support_files_list: list[tuple[str, str]] = []
    if projection["type_defs"]:
        package_name = str(projection["types_package"])
        filename = f"{package_name}.sv"
        support_files_list.append(
            (filename, _render_opentitan_public_types_package(package_name, projection))
        )

    if any(
        str(port["native_type"]) in {"tlul_pkg::tl_h2d_t", "tlul_pkg::tl_d2h_t"}
        for port in projection["ports"]
    ):
        tlul_package_name = f"{task_id}_public_tlul_pkg"
        projection["tlul_package"] = tlul_package_name
        support_files_list.append(
            (
                f"{tlul_package_name}.sv",
                _render_opentitan_public_tlul_package(tlul_package_name, projection),
            )
        )

    reg_metadata = _load_opentitan_reg_metadata(task_id, source_root)
    if reg_metadata is not None:
        regs_package_name = f"{task_id}_public_regs_pkg"
        projection["register_package"] = regs_package_name
        support_files_list.append(
            (
                f"{regs_package_name}.sv",
                _render_opentitan_public_regs_package(regs_package_name, reg_metadata),
            )
        )

    projection["support_files"] = [filename for filename, _ in support_files_list]

    hidden_metadata = {
        "profile": _OPENTITAN_SELF_CONTAINED_PROFILE,
        "native_interface": native_interface,
        "projection": projection,
    }
    return PreparedPublicInterfaceContract(
        interface=projected_interface,
        support_files=tuple(support_files_list),
        hidden_metadata=hidden_metadata,
    )


def _project_opentitan_parameters(
    raw_parameters: Any,
    *,
    implicit_params: Mapping[str, int],
) -> list[dict[str, str]]:
    parameters = _normalize_parameters(raw_parameters)
    projected: list[dict[str, str]] = []
    available_names = set(implicit_params)
    for parameter in parameters:
        raw_value = parameter.get("value")
        if raw_value is None:
            projected.append({"name": parameter["name"]})
            available_names.add(parameter["name"])
            continue
        value = _substitute_known_ints(raw_value, implicit_params)
        value = _normalize_parameter_value(value)
        if not _parameter_value_is_self_contained(value, available_names):
            continue
        projected.append({"name": parameter["name"], "value": value})
        available_names.add(parameter["name"])
    return projected


def _project_opentitan_ports(
    raw_ports: Any,
    *,
    task_id: str,
    parameter_names: tuple[str, ...],
    implicit_params: Mapping[str, int],
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    ports = _normalize_ports(raw_ports)
    projected_ports: list[dict[str, str]] = []
    opaque_ports: list[dict[str, Any]] = []
    type_defs: list[dict[str, Any]] = []
    parameter_name_set = set(parameter_names)
    types_package = f"{task_id}_public_types_pkg"
    for port in ports:
        raw_width = str(port.get("width", "")).strip()
        substituted_width = _substitute_known_ints(raw_width, implicit_params)
        public_width = substituted_width
        cast_required = False
        if raw_width and not _width_is_self_contained(substituted_width, parameter_name_set):
            bit_width = _resolve_opentitan_type_width(substituted_width)
            alias_name = f"{task_id}_{port['name']}_t"
            public_width = f"{types_package}::{alias_name}"
            cast_required = True
            type_defs.append(
                {
                    "alias_name": alias_name,
                    "bit_width": bit_width,
                    "native_type": raw_width,
                }
            )
        projected_port = {
            "name": port["name"],
            "direction": port["direction"],
        }
        if public_width:
            projected_port["width"] = public_width
        if port.get("description"):
            projected_port["description"] = str(port["description"])
        projected_ports.append(projected_port)
        opaque_ports.append(
            {
                "name": port["name"],
                "direction": port["direction"],
                "native_type": raw_width or "logic",
                "public_type": public_width or "logic",
                "cast_required": cast_required,
            }
        )
    return projected_ports, {
        "types_package": types_package,
        "support_files": [],
        "ports": opaque_ports,
        "type_defs": type_defs,
    }


def _render_opentitan_public_types_package(package_name: str, projection: Mapping[str, Any]) -> str:
    lines = [
        "// Generated public ABI types for a self-contained OpenTitan task boundary.",
        f"package {package_name};",
    ]
    for type_def in projection.get("type_defs", []):
        bit_width = int(type_def["bit_width"])
        alias_name = str(type_def["alias_name"])
        if bit_width == 1:
            lines.append(f"  typedef logic {alias_name};")
        else:
            lines.append(f"  typedef logic [{bit_width - 1}:0] {alias_name};")
    lines.append(f"endpackage : {package_name}")
    lines.append("")
    return "\n".join(lines)


def _render_opentitan_public_tlul_package(package_name: str, projection: Mapping[str, Any]) -> str:
    types_package = str(projection["types_package"])
    h2d_port = next(
        (port for port in projection["ports"] if str(port["native_type"]) == "tlul_pkg::tl_h2d_t"),
        None,
    )
    d2h_port = next(
        (port for port in projection["ports"] if str(port["native_type"]) == "tlul_pkg::tl_d2h_t"),
        None,
    )
    lines = [
        "// Generated TL-UL helper package for the self-contained public OpenTitan task ABI.",
        f"package {package_name};",
        f"  import {types_package}::*;",
        "",
        "  localparam logic [2:0] TL_A_PUTFULL    = 3'd0;",
        "  localparam logic [2:0] TL_A_PUTPARTIAL = 3'd1;",
        "  localparam logic [2:0] TL_A_GET        = 3'd4;",
        "  localparam logic [2:0] TL_D_ACK        = 3'd0;",
        "  localparam logic [2:0] TL_D_ACKDATA    = 3'd1;",
        "",
        "  localparam int unsigned TL_A_VALID_BIT      = 108;",
        "  localparam int unsigned TL_A_OPCODE_MSB     = 107;",
        "  localparam int unsigned TL_A_OPCODE_LSB     = 105;",
        "  localparam int unsigned TL_A_PARAM_MSB      = 104;",
        "  localparam int unsigned TL_A_PARAM_LSB      = 102;",
        "  localparam int unsigned TL_A_SIZE_MSB       = 101;",
        "  localparam int unsigned TL_A_SIZE_LSB       = 100;",
        "  localparam int unsigned TL_A_SOURCE_MSB     = 99;",
        "  localparam int unsigned TL_A_SOURCE_LSB     = 92;",
        "  localparam int unsigned TL_A_ADDRESS_MSB    = 91;",
        "  localparam int unsigned TL_A_ADDRESS_LSB    = 60;",
        "  localparam int unsigned TL_A_MASK_MSB       = 59;",
        "  localparam int unsigned TL_A_MASK_LSB       = 56;",
        "  localparam int unsigned TL_A_DATA_MSB       = 55;",
        "  localparam int unsigned TL_A_DATA_LSB       = 24;",
        "  localparam int unsigned TL_A_USER_MSB       = 23;",
        "  localparam int unsigned TL_A_USER_LSB       = 1;",
        "  localparam int unsigned TL_A_RSVD_MSB       = 23;",
        "  localparam int unsigned TL_A_RSVD_LSB       = 19;",
        "  localparam int unsigned TL_A_INSTR_TYPE_MSB = 18;",
        "  localparam int unsigned TL_A_INSTR_TYPE_LSB = 15;",
        "  localparam int unsigned TL_A_CMD_INTG_MSB   = 14;",
        "  localparam int unsigned TL_A_CMD_INTG_LSB   = 8;",
        "  localparam int unsigned TL_A_DATA_INTG_MSB  = 7;",
        "  localparam int unsigned TL_A_DATA_INTG_LSB  = 1;",
        "  localparam int unsigned TL_D_READY_BIT      = 0;",
        "",
        "  localparam int unsigned TL_D_VALID_BIT      = 65;",
        "  localparam int unsigned TL_D_OPCODE_MSB     = 64;",
        "  localparam int unsigned TL_D_OPCODE_LSB     = 62;",
        "  localparam int unsigned TL_D_PARAM_MSB      = 61;",
        "  localparam int unsigned TL_D_PARAM_LSB      = 59;",
        "  localparam int unsigned TL_D_SIZE_MSB       = 58;",
        "  localparam int unsigned TL_D_SIZE_LSB       = 57;",
        "  localparam int unsigned TL_D_SOURCE_MSB     = 56;",
        "  localparam int unsigned TL_D_SOURCE_LSB     = 49;",
        "  localparam int unsigned TL_D_SINK_BIT       = 48;",
        "  localparam int unsigned TL_D_DATA_MSB       = 47;",
        "  localparam int unsigned TL_D_DATA_LSB       = 16;",
        "  localparam int unsigned TL_D_USER_MSB       = 15;",
        "  localparam int unsigned TL_D_USER_LSB       = 2;",
        "  localparam int unsigned TL_D_RSP_INTG_MSB   = 15;",
        "  localparam int unsigned TL_D_RSP_INTG_LSB   = 9;",
        "  localparam int unsigned TL_D_DATA_INTG_MSB  = 8;",
        "  localparam int unsigned TL_D_DATA_INTG_LSB  = 2;",
        "  localparam int unsigned TL_D_ERROR_BIT      = 1;",
        "  localparam int unsigned TL_A_READY_BIT      = 0;",
        "",
    ]
    if h2d_port is not None:
        h2d_type = str(h2d_port["public_type"])
        prefix = _tlul_helper_prefix(str(h2d_port["name"]))
        lines.extend(
            [
                f"  function automatic {h2d_type} {prefix}_idle();",
                f"    {h2d_type} req;",
                "    req = '0;",
                "    req[TL_D_READY_BIT] = 1'b1;",
                "    return req;",
                "  endfunction",
                "",
                f"  function automatic {h2d_type} {prefix}_make_get32(",
                "    input logic [31:0] addr,",
                "    input logic [7:0] source",
                "  );",
                f"    {h2d_type} req;",
                f"    req = {prefix}_idle();",
                "    req[TL_A_VALID_BIT] = 1'b1;",
                "    req[TL_A_OPCODE_MSB:TL_A_OPCODE_LSB] = TL_A_GET;",
                "    req[TL_A_SIZE_MSB:TL_A_SIZE_LSB] = 2'd2;",
                "    req[TL_A_SOURCE_MSB:TL_A_SOURCE_LSB] = source;",
                "    req[TL_A_ADDRESS_MSB:TL_A_ADDRESS_LSB] = addr;",
                "    req[TL_A_MASK_MSB:TL_A_MASK_LSB] = 4'hf;",
                "    return req;",
                "  endfunction",
                "",
                f"  function automatic {h2d_type} {prefix}_make_put32(",
                "    input logic [31:0] addr,",
                "    input logic [31:0] data,",
                "    input logic [3:0] mask,",
                "    input logic [7:0] source",
                "  );",
                f"    {h2d_type} req;",
                f"    req = {prefix}_idle();",
                "    req[TL_A_VALID_BIT] = 1'b1;",
                "    req[TL_A_OPCODE_MSB:TL_A_OPCODE_LSB] = TL_A_PUTFULL;",
                "    req[TL_A_SIZE_MSB:TL_A_SIZE_LSB] = 2'd2;",
                "    req[TL_A_SOURCE_MSB:TL_A_SOURCE_LSB] = source;",
                "    req[TL_A_ADDRESS_MSB:TL_A_ADDRESS_LSB] = addr;",
                "    req[TL_A_MASK_MSB:TL_A_MASK_LSB] = mask;",
                "    req[TL_A_DATA_MSB:TL_A_DATA_LSB] = data;",
                "    return req;",
                "  endfunction",
                "",
                f"  function automatic {h2d_type} {prefix}_make_putpartial32(",
                "    input logic [31:0] addr,",
                "    input logic [31:0] data,",
                "    input logic [3:0] mask,",
                "    input logic [7:0] source",
                "  );",
                f"    {h2d_type} req;",
                f"    req = {prefix}_idle();",
                "    req[TL_A_VALID_BIT] = 1'b1;",
                "    req[TL_A_OPCODE_MSB:TL_A_OPCODE_LSB] = TL_A_PUTPARTIAL;",
                "    req[TL_A_SIZE_MSB:TL_A_SIZE_LSB] = 2'd2;",
                "    req[TL_A_SOURCE_MSB:TL_A_SOURCE_LSB] = source;",
                "    req[TL_A_ADDRESS_MSB:TL_A_ADDRESS_LSB] = addr;",
                "    req[TL_A_MASK_MSB:TL_A_MASK_LSB] = mask;",
                "    req[TL_A_DATA_MSB:TL_A_DATA_LSB] = data;",
                "    return req;",
                "  endfunction",
                "",
                f"  function automatic {h2d_type} {prefix}_with_param(",
                f"    input {h2d_type} req,",
                "    input logic [2:0] param",
                "  );",
                f"    {prefix}_with_param = req;",
                f"    {prefix}_with_param[TL_A_PARAM_MSB:TL_A_PARAM_LSB] = param;",
                "  endfunction",
                "",
                f"  function automatic {h2d_type} {prefix}_with_user(",
                f"    input {h2d_type} req,",
                "    input logic [3:0] instr_type,",
                "    input logic [6:0] cmd_intg,",
                "    input logic [6:0] data_intg",
                "  );",
                f"    {prefix}_with_user = req;",
                f"    {prefix}_with_user[TL_A_INSTR_TYPE_MSB:TL_A_INSTR_TYPE_LSB] = instr_type;",
                f"    {prefix}_with_user[TL_A_CMD_INTG_MSB:TL_A_CMD_INTG_LSB] = cmd_intg;",
                f"    {prefix}_with_user[TL_A_DATA_INTG_MSB:TL_A_DATA_INTG_LSB] = data_intg;",
                "  endfunction",
                "",
                f"  function automatic logic {prefix}_valid(input {h2d_type} req);",
                "    return req[TL_A_VALID_BIT];",
                "  endfunction",
                "",
                f"  function automatic logic [2:0] {prefix}_opcode(input {h2d_type} req);",
                "    return req[TL_A_OPCODE_MSB:TL_A_OPCODE_LSB];",
                "  endfunction",
                "",
                f"  function automatic logic [2:0] {prefix}_param(input {h2d_type} req);",
                "    return req[TL_A_PARAM_MSB:TL_A_PARAM_LSB];",
                "  endfunction",
                "",
                f"  function automatic logic [1:0] {prefix}_size(input {h2d_type} req);",
                "    return req[TL_A_SIZE_MSB:TL_A_SIZE_LSB];",
                "  endfunction",
                "",
                f"  function automatic logic [7:0] {prefix}_source(input {h2d_type} req);",
                "    return req[TL_A_SOURCE_MSB:TL_A_SOURCE_LSB];",
                "  endfunction",
                "",
                f"  function automatic logic [31:0] {prefix}_address(input {h2d_type} req);",
                "    return req[TL_A_ADDRESS_MSB:TL_A_ADDRESS_LSB];",
                "  endfunction",
                "",
                f"  function automatic logic [3:0] {prefix}_mask(input {h2d_type} req);",
                "    return req[TL_A_MASK_MSB:TL_A_MASK_LSB];",
                "  endfunction",
                "",
                f"  function automatic logic [31:0] {prefix}_data(input {h2d_type} req);",
                "    return req[TL_A_DATA_MSB:TL_A_DATA_LSB];",
                "  endfunction",
                "",
                f"  function automatic logic [3:0] {prefix}_instr_type(input {h2d_type} req);",
                "    return req[TL_A_INSTR_TYPE_MSB:TL_A_INSTR_TYPE_LSB];",
                "  endfunction",
                "",
                f"  function automatic logic [6:0] {prefix}_cmd_intg(input {h2d_type} req);",
                "    return req[TL_A_CMD_INTG_MSB:TL_A_CMD_INTG_LSB];",
                "  endfunction",
                "",
                f"  function automatic logic [6:0] {prefix}_data_intg(input {h2d_type} req);",
                "    return req[TL_A_DATA_INTG_MSB:TL_A_DATA_INTG_LSB];",
                "  endfunction",
                "",
                f"  function automatic logic {prefix}_d_ready(input {h2d_type} req);",
                "    return req[TL_D_READY_BIT];",
                "  endfunction",
                "",
            ]
        )
    if d2h_port is not None:
        d2h_type = str(d2h_port["public_type"])
        prefix = _tlul_helper_prefix(str(d2h_port["name"]))
        lines.extend(
            [
                f"  function automatic logic {prefix}_valid(input {d2h_type} rsp);",
                "    return rsp[TL_D_VALID_BIT];",
                "  endfunction",
                "",
                f"  function automatic logic [2:0] {prefix}_opcode(input {d2h_type} rsp);",
                "    return rsp[TL_D_OPCODE_MSB:TL_D_OPCODE_LSB];",
                "  endfunction",
                "",
                f"  function automatic logic [2:0] {prefix}_param(input {d2h_type} rsp);",
                "    return rsp[TL_D_PARAM_MSB:TL_D_PARAM_LSB];",
                "  endfunction",
                "",
                f"  function automatic logic [1:0] {prefix}_size(input {d2h_type} rsp);",
                "    return rsp[TL_D_SIZE_MSB:TL_D_SIZE_LSB];",
                "  endfunction",
                "",
                f"  function automatic logic [7:0] {prefix}_source(input {d2h_type} rsp);",
                "    return rsp[TL_D_SOURCE_MSB:TL_D_SOURCE_LSB];",
                "  endfunction",
                "",
                f"  function automatic logic {prefix}_sink(input {d2h_type} rsp);",
                "    return rsp[TL_D_SINK_BIT];",
                "  endfunction",
                "",
                f"  function automatic logic [31:0] {prefix}_data(input {d2h_type} rsp);",
                "    return rsp[TL_D_DATA_MSB:TL_D_DATA_LSB];",
                "  endfunction",
                "",
                f"  function automatic logic [6:0] {prefix}_rsp_intg(input {d2h_type} rsp);",
                "    return rsp[TL_D_RSP_INTG_MSB:TL_D_RSP_INTG_LSB];",
                "  endfunction",
                "",
                f"  function automatic logic [6:0] {prefix}_data_intg(input {d2h_type} rsp);",
                "    return rsp[TL_D_DATA_INTG_MSB:TL_D_DATA_INTG_LSB];",
                "  endfunction",
                "",
                f"  function automatic logic {prefix}_error(input {d2h_type} rsp);",
                "    return rsp[TL_D_ERROR_BIT];",
                "  endfunction",
                "",
                f"  function automatic logic {prefix}_ready(input {d2h_type} rsp);",
                "    return rsp[TL_A_READY_BIT];",
                "  endfunction",
                "",
            ]
        )
    lines.append(f"endpackage : {package_name}")
    lines.append("")
    return "\n".join(lines)


def _tlul_helper_prefix(port_name: str) -> str:
    if port_name == "tl_i":
        return "tl"
    if port_name == "tl_o":
        return "tl_rsp"
    return re.sub(r"[^A-Za-z0-9_]+", "_", port_name).strip("_") or "tl"


def _render_opentitan_public_regs_package(package_name: str, reg_metadata: Mapping[str, Any]) -> str:
    lines = [
        "// Generated register and field constants for the self-contained public OpenTitan task ABI.",
        f"package {package_name};",
    ]
    for entry in reg_metadata.get("entries", ()):
        kind = str(entry["kind"])
        prefix = _sv_const_name(str(entry["name"]))
        if kind in {"window", "multireg"}:
            lines.append(
                f"  localparam logic [31:0] {prefix}_OFFSET = 32'h{int(entry['offset']) & 0xffffffff:08x};"
            )
        if kind == "window":
            lines.append(f"  localparam int unsigned {prefix}_ITEMS = {int(entry['items'])};")
            lines.append(
                f"  localparam int unsigned {prefix}_SIZE_BYTES = {int(entry['size_in_bytes'])};"
            )
            lines.append(
                f"  localparam int unsigned {prefix}_VALID_BITS = {int(entry['valid_bits'])};"
            )
            lines.append("")
            continue
        if kind == "multireg":
            lines.append(f"  localparam int unsigned {prefix}_COUNT = {int(entry['count'])};")
            lines.append(f"  localparam int unsigned {prefix}_STRIDE = {int(entry['stride'])};")
            lines.append("")
            for reg in entry.get("registers", ()):
                lines.extend(_render_register_constants(reg))
            continue
        lines.extend(_render_register_constants(entry))
    lines.append(f"endpackage : {package_name}")
    lines.append("")
    return "\n".join(lines)


def _render_register_constants(entry: Mapping[str, Any]) -> list[str]:
    prefix = _sv_const_name(str(entry["name"]))
    lines = [f"  localparam logic [31:0] {prefix}_OFFSET = 32'h{int(entry['offset']) & 0xffffffff:08x};"]
    for field in entry.get("fields", ()):
        field_prefix = f"{prefix}_{_sv_const_name(str(field['name']))}"
        lsb = int(field["lsb"])
        width = int(field["width"])
        if width <= 0:
            continue
        mask = ((1 << width) - 1) << lsb
        lines.append(f"  localparam int unsigned {field_prefix}_LSB = {lsb};")
        lines.append(f"  localparam int unsigned {field_prefix}_WIDTH = {width};")
        lines.append(f"  localparam logic [31:0] {field_prefix}_MASK = 32'h{mask & 0xffffffff:08x};")
    lines.append("")
    return lines


def _sv_const_name(name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_").upper()
    if not sanitized:
        return "UNNAMED"
    if sanitized[0].isdigit():
        return f"_{sanitized}"
    return sanitized


@lru_cache(maxsize=None)
def _load_opentitan_reg_metadata(task_id: str, source_root: Path | None) -> dict[str, Any] | None:
    if source_root is None:
        return None
    resolved_root = source_root.expanduser().resolve()
    hjson_path = resolved_root / "hw" / "ip" / task_id / "data" / f"{task_id}.hjson"
    if not hjson_path.exists():
        return None
    try:
        import hjson  # type: ignore
    except Exception:
        return None
    try:
        raw = hjson.loads(hjson_path.read_text(), use_decimal=True)
    except Exception:
        return None
    if not isinstance(raw, Mapping):
        return None
    reg_entries = raw.get("registers")
    if not isinstance(reg_entries, list):
        return None

    regwidth_bits = _safe_eval_int_expression(str(raw.get("regwidth", "32")))
    word_bytes = max(1, (regwidth_bits + 7) // 8)
    params = _load_opentitan_hjson_param_defaults(raw)

    entries: list[dict[str, Any]] = []
    explicit_register_names = _collect_opentitan_register_names(reg_entries)
    synthesized_entries = _synthesize_opentitan_special_registers(
        raw,
        explicit_register_names=explicit_register_names,
    )
    entries.extend(synthesized_entries)
    current_offset = word_bytes * len(synthesized_entries)
    for raw_entry in reg_entries:
        if not isinstance(raw_entry, Mapping):
            continue
        if "skipto" in raw_entry:
            current_offset = _safe_eval_int_expression(
                _substitute_known_ints(str(raw_entry["skipto"]), params)
            )
            continue
        if "reserved" in raw_entry:
            current_offset += word_bytes * _safe_eval_int_expression(
                _substitute_known_ints(str(raw_entry["reserved"]), params)
            )
            continue
        if "sameaddr" in raw_entry:
            sameaddr = raw_entry["sameaddr"]
            if isinstance(sameaddr, list):
                for sameaddr_reg in sameaddr:
                    if isinstance(sameaddr_reg, Mapping):
                        entries.append(
                            _serialize_opentitan_register_entry(
                                sameaddr_reg,
                                offset=current_offset,
                                params=params,
                            )
                        )
                current_offset += word_bytes
            continue
        if "window" in raw_entry:
            window = raw_entry["window"]
            if not isinstance(window, Mapping):
                continue
            items = _safe_eval_int_expression(_substitute_known_ints(str(window.get("items", "1")), params))
            valid_bits = _safe_eval_int_expression(
                _substitute_known_ints(str(window.get("validbits", regwidth_bits)), params)
            )
            entries.append(
                {
                    "kind": "window",
                    "name": str(window["name"]),
                    "offset": current_offset,
                    "items": items,
                    "size_in_bytes": word_bytes * items,
                    "valid_bits": valid_bits,
                }
            )
            current_offset += word_bytes * items
            continue
        if "multireg" in raw_entry:
            multireg = raw_entry["multireg"]
            if not isinstance(multireg, Mapping):
                continue
            count = _safe_eval_int_expression(
                _substitute_known_ints(str(multireg.get("count", "1")), params)
            )
            stride = word_bytes
            fields = _serialize_opentitan_fields(multireg.get("fields"), params=params)
            registers = [
                {
                    "kind": "register",
                    "name": f"{multireg['name']}_{index}",
                    "offset": current_offset + index * stride,
                    "fields": fields,
                }
                for index in range(count)
            ]
            entries.append(
                {
                    "kind": "multireg",
                    "name": str(multireg["name"]),
                    "offset": current_offset,
                    "count": count,
                    "stride": stride,
                    "registers": registers,
                }
            )
            current_offset += count * stride
            continue

        entries.append(
            _serialize_opentitan_register_entry(
                raw_entry,
                offset=current_offset,
                params=params,
            )
        )
        current_offset += word_bytes
    return {"entries": entries}


def _collect_opentitan_register_names(reg_entries: list[Any]) -> set[str]:
    names: set[str] = set()
    for raw_entry in reg_entries:
        if not isinstance(raw_entry, Mapping):
            continue
        if "name" in raw_entry:
            names.add(str(raw_entry["name"]).upper())
        if "multireg" in raw_entry and isinstance(raw_entry["multireg"], Mapping):
            names.add(str(raw_entry["multireg"].get("name", "")).upper())
        if "window" in raw_entry and isinstance(raw_entry["window"], Mapping):
            names.add(str(raw_entry["window"].get("name", "")).upper())
        if "sameaddr" in raw_entry and isinstance(raw_entry["sameaddr"], list):
            for sameaddr_reg in raw_entry["sameaddr"]:
                if isinstance(sameaddr_reg, Mapping) and "name" in sameaddr_reg:
                    names.add(str(sameaddr_reg["name"]).upper())
    return names


def _synthesize_opentitan_special_registers(
    raw: Mapping[str, Any],
    *,
    explicit_register_names: set[str],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    alert_list = raw.get("alert_list")
    if (
        isinstance(alert_list, list)
        and alert_list
        and "ALERT_TEST" not in explicit_register_names
    ):
        alert_fields: list[dict[str, Any]] = []
        for bit_index, raw_alert in enumerate(alert_list):
            if not isinstance(raw_alert, Mapping) or "name" not in raw_alert:
                continue
            alert_fields.append(
                {
                    "name": str(raw_alert["name"]),
                    "lsb": bit_index,
                    "width": 1,
                }
            )
        if alert_fields:
            entries.append(
                {
                    "kind": "register",
                    "name": "ALERT_TEST",
                    "offset": 0,
                    "fields": alert_fields,
                }
            )
    return entries


def _load_opentitan_hjson_param_defaults(raw: Mapping[str, Any]) -> dict[str, int]:
    param_list = raw.get("param_list", ())
    if not isinstance(param_list, list):
        return {}
    defaults: dict[str, int] = {}
    for param in param_list:
        if not isinstance(param, Mapping) or "name" not in param or "default" not in param:
            continue
        default_expr = str(param["default"]).strip()
        if "'" in default_expr:
            continue
        try:
            defaults[str(param["name"])] = _safe_eval_int_expression(default_expr)
        except Exception:
            continue
    return defaults


def _serialize_opentitan_register_entry(
    entry: Mapping[str, Any],
    *,
    offset: int,
    params: Mapping[str, int],
) -> dict[str, Any]:
    return {
        "kind": "register",
        "name": str(entry["name"]),
        "offset": int(offset),
        "fields": _serialize_opentitan_fields(entry.get("fields"), params=params),
    }


def _resolve_opentitan_implicit_parameters(task_id: str, source_root: Path | None) -> dict[str, int]:
    if source_root is None:
        return {}
    reg_pkg_path = source_root.expanduser().resolve() / "hw" / "ip" / task_id / "rtl" / f"{task_id}_reg_pkg.sv"
    if not reg_pkg_path.exists():
        return {}
    values: dict[str, int] = {}
    text = reg_pkg_path.read_text()
    for match in _REG_PKG_PARAM_RE.finditer(text):
        values[match.group("name")] = _safe_eval_int_expression(match.group("value"))
    return values


def _serialize_opentitan_fields(
    raw_fields: Any,
    *,
    params: Mapping[str, int],
) -> list[dict[str, Any]]:
    if not isinstance(raw_fields, list):
        return []
    fields: list[dict[str, Any]] = []
    for raw_field in raw_fields:
        if not isinstance(raw_field, Mapping) or "bits" not in raw_field or "name" not in raw_field:
            continue
        lsb, width = _parse_opentitan_bits(str(raw_field["bits"]), params=params)
        fields.append(
            {
                "name": str(raw_field["name"]),
                "lsb": lsb,
                "width": width,
            }
        )
    return fields


def _parse_opentitan_bits(bits: str, *, params: Mapping[str, int]) -> tuple[int, int]:
    substituted = _substitute_known_ints(bits.strip(), params)
    if ":" not in substituted:
        lsb = _safe_eval_int_expression(substituted)
        return lsb, 1
    hi_expr, lo_expr = substituted.split(":", 1)
    hi = _safe_eval_int_expression(hi_expr)
    lo = _safe_eval_int_expression(lo_expr)
    lsb = min(hi, lo)
    return lsb, abs(hi - lo) + 1


def _normalize_parameter_value(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("'{"):
        return "'0"
    match = _REPLICATION_RE.fullmatch(stripped)
    if match is None:
        return stripped
    count = int(match.group(1))
    body = match.group(2).strip()
    if body == "0":
        bit = "0"
    elif body == "1":
        bit = "1"
    elif body in {"1'b0", "1'h0"}:
        bit = "0"
    elif body in {"1'b1", "1'h1"}:
        bit = "1"
    else:
        return stripped
    return f"{count}'b{bit * count}"


def _parameter_value_is_self_contained(value: str, available_names: set[str]) -> bool:
    if "::" in value:
        return False
    identifiers = {
        ident
        for ident in _SV_IDENT_RE.findall(value)
        if ident not in _SV_KEYWORDS
    }
    return identifiers <= available_names


def _width_is_self_contained(width: str, parameter_names: set[str]) -> bool:
    if not width:
        return True
    if "::" in width:
        return False
    identifiers = {
        ident
        for ident in _SV_IDENT_RE.findall(width)
        if ident not in _SV_KEYWORDS
    }
    return identifiers <= parameter_names


def _resolve_opentitan_type_width(width: str) -> int:
    stripped = width.strip()
    match = _ARRAY_TYPE_RE.fullmatch(stripped)
    if match is None:
        raise ValueError(f"unable to project OpenTitan public type {width!r}")
    base = match.group("base")
    base_width = _OPENTITAN_OPAQUE_TYPE_WIDTHS.get(base)
    if base_width is None:
        raise ValueError(f"unsupported OpenTitan opaque type {base!r}")
    total_width = base_width
    dims = match.group("dims")
    for hi_expr, lo_expr in _PACKED_DIM_RE.findall(dims):
        hi = _safe_eval_int_expression(hi_expr)
        lo = _safe_eval_int_expression(lo_expr)
        total_width *= abs(hi - lo) + 1
    return total_width


def _substitute_known_ints(text: str, known_values: Mapping[str, int]) -> str:
    result = str(text)
    for name, value in known_values.items():
        result = re.sub(rf"\b{re.escape(name)}\b", str(value), result)
    return result


def _safe_eval_int_expression(expr: str) -> int:
    parsed = ast.parse(expr.strip(), mode="eval")
    return _eval_int_ast(parsed.body)


def _eval_int_ast(node: ast.AST) -> int:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return int(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _eval_int_ast(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Div)):
        left = _eval_int_ast(node.left)
        right = _eval_int_ast(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if right == 0:
            raise ValueError("division by zero in SV width expression")
        return left // right
    raise ValueError(f"unsupported integer expression {ast.dump(node)}")
