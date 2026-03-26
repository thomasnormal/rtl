from pathlib import Path

from rtl_training.interface_contracts import (
    materialize_public_interface_sv,
    normalize_public_interface_contract,
)


def test_normalize_public_interface_contract_derives_ports_from_inputs_outputs() -> None:
    interface = normalize_public_interface_contract(
        {
            "top_module": "uart",
            "declared_module_name": "uart",
            "inputs": [
                {"name": "clk_i", "direction": "input", "width": "logic"},
                {"name": "tl_i", "direction": "input", "width": "tlul_pkg::tl_h2d_t"},
            ],
            "outputs": [
                {"name": "tl_o", "direction": "output", "width": "tlul_pkg::tl_d2h_t"},
            ],
            "parameters": [
                {"name": "AlertSkewCycles", "value": "1"},
            ],
        },
        candidate_top_module="uart",
    )

    assert interface["ports"] == [
        {"name": "clk_i", "direction": "input", "width": "logic"},
        {"name": "tl_i", "direction": "input", "width": "tlul_pkg::tl_h2d_t"},
        {"name": "tl_o", "direction": "output", "width": "tlul_pkg::tl_d2h_t"},
    ]
    assert interface["modports"] == [
        {
            "name": "dut",
            "signals": [
                {"name": "clk_i", "direction": "input"},
                {"name": "tl_i", "direction": "input"},
                {"name": "tl_o", "direction": "output"},
            ],
        },
        {
            "name": "tb",
            "signals": [
                {"name": "clk_i", "direction": "output"},
                {"name": "tl_i", "direction": "output"},
                {"name": "tl_o", "direction": "input"},
            ],
        },
    ]


def test_materialize_public_interface_sv_writes_sv_interface_and_readme(tmp_path: Path) -> None:
    interface = normalize_public_interface_contract(
        {
            "top_module": "RAM",
            "declared_module_name": "RAM",
            "ports": [
                {"name": "clk", "direction": "input"},
                {"name": "write_addr", "direction": "input", "width": "[7:0]"},
                {"name": "read_data", "direction": "output", "width": "[5:0]"},
            ],
            "parameters": [
                {"name": "DEPTH", "value": "8"},
            ],
        },
        candidate_top_module="RAM",
    )

    written = materialize_public_interface_sv(tmp_path, interface)

    assert written.interface_dir == tmp_path / "interface"
    assert written.readme_path.exists()
    assert written.sv_path.exists()

    content = written.sv_path.read_text()
    assert "interface RAM_public_if" in content
    assert "parameter DEPTH = 8" in content
    assert "logic clk;" in content
    assert "logic [7:0] write_addr;" in content
    assert "logic [5:0] read_data;" in content
    assert "modport dut (" in content
    assert "input clk" in content
    assert "output read_data" in content

