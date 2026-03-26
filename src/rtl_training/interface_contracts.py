from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping


_PORT_DIRECTIONS = frozenset({"input", "output", "inout"})
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

_OPENTITAN_SELF_CONTAINED_PROFILE = "opentitan_self_contained_v1"
_OPENTITAN_OPAQUE_TYPE_WIDTHS = {
    "dma_pkg::lsio_trigger_t": 11,
    "dma_pkg::sys_req_t": 184,
    "dma_pkg::sys_rsp_t": 40,
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
        "// Generated from task/task.json public interface metadata.",
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
        "This directory is generated from `task/task.json` and provides the",
        "public DUT boundary as SystemVerilog artifacts.",
        "",
        f"- `{sv_filename}` defines `{interface_name}` with canonical `dut` and `tb` modports.",
    ]
    for support_file in support_files:
        lines.append(f"- `{support_file}` provides self-contained public SV support types for the task.")
    lines.extend(
        [
            "- These files describe the public boundary only. Hidden oracles and deep-DV",
            "  compatibility ABIs live elsewhere.",
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

    support_files: tuple[tuple[str, str], ...] = ()
    if projection["support_files"]:
        package_name = str(projection["types_package"])
        filename = f"{package_name}.sv"
        support_files = ((filename, _render_opentitan_public_types_package(package_name, projection)),)

    hidden_metadata = {
        "profile": _OPENTITAN_SELF_CONTAINED_PROFILE,
        "native_interface": native_interface,
        "projection": projection,
    }
    return PreparedPublicInterfaceContract(
        interface=projected_interface,
        support_files=support_files,
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
        "support_files": [f"{types_package}.sv"] if type_defs else [],
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
        native_type = str(type_def["native_type"])
        if bit_width == 1:
            lines.append(f"  typedef logic {alias_name}; // native: {native_type}")
        else:
            lines.append(
                f"  typedef logic [{bit_width - 1}:0] {alias_name}; // native: {native_type}"
            )
    lines.append(f"endpackage : {package_name}")
    lines.append("")
    return "\n".join(lines)


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
