from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


_PORT_DIRECTIONS = frozenset({"input", "output", "inout"})


@dataclass(frozen=True)
class MaterializedPublicInterfaceSv:
    interface_dir: Path
    readme_path: Path
    sv_path: Path


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
) -> MaterializedPublicInterfaceSv:
    spec_dir_path = Path(spec_dir)
    interface_dir = spec_dir_path / "interface"
    interface_dir.mkdir(parents=True, exist_ok=True)

    top_module = str(interface["top_module"])
    interface_name = f"{top_module}_public_if"
    sv_path = interface_dir / f"{interface_name}.sv"
    readme_path = interface_dir / "README.md"

    sv_path.write_text(_render_public_interface_sv(interface_name, interface))
    readme_path.write_text(_render_interface_readme(interface_name, sv_path.name))

    return MaterializedPublicInterfaceSv(
        interface_dir=interface_dir,
        readme_path=readme_path,
        sv_path=sv_path,
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


def _render_public_interface_sv(interface_name: str, interface: Mapping[str, Any]) -> str:
    parameters = interface.get("parameters", [])
    ports = interface.get("ports", [])
    modports = interface.get("modports", [])

    lines: list[str] = [
        "// Generated from task/task.json public interface metadata.",
        "// This is the machine-checkable SV form of the public DUT boundary.",
    ]

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


def _render_interface_readme(interface_name: str, sv_filename: str) -> str:
    return "\n".join(
        [
            "# Public SV Interface Contract",
            "",
            "This directory is generated from `task/task.json` and provides the",
            "public DUT boundary as SystemVerilog artifacts.",
            "",
            f"- `{sv_filename}` defines `{interface_name}` with canonical `dut` and `tb` modports.",
            "- These files describe the public boundary only. Hidden oracles and deep-DV",
            "  compatibility ABIs live elsewhere.",
            "- Package-qualified types are preserved verbatim from the task metadata, so",
            "  compiling these files may require additional package definitions from the task spec.",
            "",
        ]
    )
