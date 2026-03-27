import json
from pathlib import Path

import pytest

from rtl_training.micro_arch_contracts import (
    discover_micro_arch_bind_module,
    discover_micro_arch_interface_spec,
    parse_micro_arch_interface_spec,
    validate_public_micro_arch_dir,
    write_micro_arch_bind_check_tb,
)


def test_parse_micro_arch_interface_spec_reads_dut_and_tb_modports(tmp_path: Path) -> None:
    interface_path = tmp_path / "rv_timer_micro_arch_if.sv"
    interface_path.write_text(
        "interface rv_timer_micro_arch_if;\n"
        "  logic ctrl_active_0;\n"
        "  logic [63:0] timer_val_0;\n"
        "  logic force_intg_error_i;\n"
        "  modport dut (\n"
        "    output ctrl_active_0,\n"
        "    output timer_val_0,\n"
        "    input force_intg_error_i\n"
        "  );\n"
        "  modport tb (\n"
        "    input ctrl_active_0,\n"
        "    input timer_val_0,\n"
        "    output force_intg_error_i\n"
        "  );\n"
        "endinterface\n"
    )

    spec = parse_micro_arch_interface_spec(interface_path)

    assert spec.interface_name == "rv_timer_micro_arch_if"
    assert spec.instance_name == "u_rv_timer_micro_arch_if"
    assert spec.signals == ("ctrl_active_0", "timer_val_0", "force_intg_error_i")
    assert spec.dut_outputs == ("ctrl_active_0", "timer_val_0")
    assert spec.dut_inputs == ("force_intg_error_i",)
    assert "tb" in spec.modports


def test_validate_public_micro_arch_dir_requires_readme_and_dut_modport(tmp_path: Path) -> None:
    spec_dir = tmp_path / "spec"
    micro_arch_dir = spec_dir / "micro_arch"
    micro_arch_dir.mkdir(parents=True)
    (micro_arch_dir / "README.md").write_text("micro arch\n")
    (micro_arch_dir / "uart_micro_arch_if.sv").write_text(
        "interface uart_micro_arch_if;\n"
        "  logic rx_sync;\n"
        "  modport dut (output rx_sync);\n"
        "  modport mon (input rx_sync);\n"
        "endinterface\n"
    )

    spec = validate_public_micro_arch_dir(spec_dir)

    assert spec is not None
    assert spec.interface_name == "uart_micro_arch_if"


def test_validate_public_micro_arch_dir_rejects_missing_dut_modport(tmp_path: Path) -> None:
    spec_dir = tmp_path / "spec"
    micro_arch_dir = spec_dir / "micro_arch"
    micro_arch_dir.mkdir(parents=True)
    (micro_arch_dir / "README.md").write_text("micro arch\n")
    (micro_arch_dir / "uart_micro_arch_if.sv").write_text(
        "interface uart_micro_arch_if;\n"
        "  logic rx_sync;\n"
        "  modport mon (input rx_sync);\n"
        "endinterface\n"
    )

    with pytest.raises(ValueError, match="dut"):
        validate_public_micro_arch_dir(spec_dir)


def test_discover_micro_arch_interface_spec_finds_materialized_micro_arch_dir(tmp_path: Path) -> None:
    spec_dir = tmp_path / "spec"
    micro_arch_dir = spec_dir / "micro_arch"
    micro_arch_dir.mkdir(parents=True)
    (micro_arch_dir / "README.md").write_text("micro arch\n")
    (micro_arch_dir / "foo_micro_arch_if.sv").write_text(
        "interface foo_micro_arch_if;\n"
        "  logic a;\n"
        "  modport dut (output a);\n"
        "  modport tb (input a);\n"
        "endinterface\n"
    )

    spec = discover_micro_arch_interface_spec(spec_dir)

    assert spec is not None
    assert spec.instance_name == "u_foo_micro_arch_if"


def test_discover_micro_arch_bind_module_reads_module_name(tmp_path: Path) -> None:
    spec_dir = tmp_path / "spec"
    micro_arch_dir = spec_dir / "micro_arch"
    micro_arch_dir.mkdir(parents=True)
    (micro_arch_dir / "README.md").write_text("micro arch\n")
    (micro_arch_dir / "foo_micro_arch_if.sv").write_text(
        "interface foo_micro_arch_if;\n"
        "  logic a;\n"
        "  modport dut (output a);\n"
        "  modport mon (input a);\n"
        "endinterface\n"
    )
    bind_path = micro_arch_dir / "foo_micro_arch_bind.sv"
    bind_path.write_text("module foo_micro_arch_bind;\nendmodule\n")

    bind_module = discover_micro_arch_bind_module(spec_dir)

    assert bind_module == ("foo_micro_arch_bind", bind_path)


def test_write_micro_arch_bind_check_tb_uses_public_ports_and_bind_module(tmp_path: Path) -> None:
    spec_dir = tmp_path / "spec"
    micro_arch_dir = spec_dir / "micro_arch"
    micro_arch_dir.mkdir(parents=True)
    (micro_arch_dir / "README.md").write_text("micro arch\n")
    (micro_arch_dir / "rv_timer_micro_arch_if.sv").write_text(
        "interface rv_timer_micro_arch_if;\n"
        "  logic ctrl_active_0;\n"
        "  modport dut (output ctrl_active_0);\n"
        "  modport tb (input ctrl_active_0);\n"
        "endinterface\n"
    )
    (micro_arch_dir / "rv_timer_micro_arch_bind.sv").write_text(
        "module rv_timer_micro_arch_bind;\n"
        "endmodule\n"
    )
    public_task_path = tmp_path / "task.json"
    public_task_path.write_text(
        json.dumps(
            {
                "candidate_top_module": "rv_timer",
                "interface": {
                    "top_module": "rv_timer",
                    "ports": [
                        {"name": "clk_i", "direction": "input", "width": "logic"},
                        {
                            "name": "tl_i",
                            "direction": "input",
                            "width": "rv_timer_public_types_pkg::rv_timer_tl_i_t",
                        },
                        {"name": "intr_o", "direction": "output", "width": "logic"},
                    ],
                },
            },
            indent=2,
        )
        + "\n"
    )
    tb_path = tmp_path / "tb_bind_check.sv"

    written = write_micro_arch_bind_check_tb(public_task_path, spec_dir, tb_path)

    assert written == tb_path
    content = tb_path.read_text()
    assert "module tb_bind_check;" in content
    assert "logic clk_i;" in content
    assert "rv_timer_public_types_pkg::rv_timer_tl_i_t tl_i;" in content
    assert "logic intr_o;" in content
    assert "rv_timer dut (" in content
    assert ".clk_i(clk_i)" in content
    assert ".tl_i(tl_i)" in content
    assert ".intr_o(intr_o)" in content
    assert "rv_timer_micro_arch_bind u_bind();" in content
