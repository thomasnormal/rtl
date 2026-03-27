from pathlib import Path

from rtl_training.interface_contracts import (
    materialize_public_interface_sv,
    normalize_public_interface_contract,
    prepare_public_interface_contract,
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


def test_prepare_opentitan_public_interface_projects_package_types_to_local_sv(tmp_path: Path) -> None:
    source_root = tmp_path / "opentitan"
    reg_pkg = source_root / "hw" / "ip" / "uart" / "rtl" / "uart_reg_pkg.sv"
    reg_pkg.parent.mkdir(parents=True)
    reg_pkg.write_text(
        "package uart_reg_pkg;\n"
        "  parameter int NumAlerts = 1;\n"
        "  parameter int NumRegs = 13;\n"
        "endpackage\n"
    )
    (source_root / "hw" / "ip" / "uart" / "data").mkdir(parents=True)
    (source_root / "hw" / "ip" / "uart" / "data" / "uart.hjson").write_text(
        "\n".join(
            [
                'name: "uart"',
                "clocking: [{clock: 'clk_i', reset: 'rst_ni', primary: true}]",
                "bus_interfaces: [{protocol: 'tlul', direction: 'device'}]",
                "alert_list: [{name: 'fatal_fault', desc: 'fatal alert'}]",
                "registers: [",
                "  {",
                "    name: 'CTRL',",
                "    desc: 'ctrl register',",
                "    swaccess: 'rw',",
                "    hwaccess: 'hro',",
                "    fields: [{bits: '3:0', name: 'TX'}]",
                "  }",
                "]",
                "",
            ]
        )
    )

    prepared = prepare_public_interface_contract(
        {
            "top_module": "uart",
            "declared_module_name": "uart",
            "parameters": [
                {"name": "AlertAsyncOn", "value": "{NumAlerts{1'b1}}"},
                {"name": "AlertSkewCycles", "value": "1"},
                {"name": "RaclPolicySelVec", "value": "'{NumRegs{0}}"},
                {"name": "EnableRacl", "value": "1'b0"},
                {"name": "RaclErrorRsp", "value": "EnableRacl"},
            ],
            "inputs": [
                {"name": "clk_i", "direction": "input", "width": "logic"},
                {"name": "tl_i", "direction": "input", "width": "tlul_pkg::tl_h2d_t"},
                {
                    "name": "alert_rx_i",
                    "direction": "input",
                    "width": "prim_alert_pkg::alert_rx_t [NumAlerts-1:0]",
                },
            ],
            "outputs": [
                {"name": "tl_o", "direction": "output", "width": "tlul_pkg::tl_d2h_t"},
            ],
        },
        candidate_top_module="uart",
        profile="opentitan_self_contained_v1",
        task_id="uart",
        source_root=source_root,
    )

    assert prepared.interface["parameters"] == [
        {"name": "AlertAsyncOn", "value": "1'b1"},
        {"name": "AlertSkewCycles", "value": "1"},
        {"name": "RaclPolicySelVec", "value": "'0"},
        {"name": "EnableRacl", "value": "1'b0"},
        {"name": "RaclErrorRsp", "value": "EnableRacl"},
    ]
    assert prepared.interface["ports"] == [
        {"name": "clk_i", "direction": "input", "width": "logic"},
        {
            "name": "tl_i",
            "direction": "input",
            "width": "uart_public_types_pkg::uart_tl_i_t",
        },
        {
            "name": "alert_rx_i",
            "direction": "input",
            "width": "uart_public_types_pkg::uart_alert_rx_i_t",
        },
        {
            "name": "tl_o",
            "direction": "output",
            "width": "uart_public_types_pkg::uart_tl_o_t",
        },
    ]
    assert dict(prepared.support_files)["uart_public_types_pkg.sv"].find(
        "typedef logic [108:0] uart_tl_i_t;"
    ) != -1
    assert dict(prepared.support_files)["uart_public_types_pkg.sv"].find(
        "typedef logic [3:0] uart_alert_rx_i_t;"
    ) != -1
    assert "tlul_pkg::" not in dict(prepared.support_files)["uart_public_types_pkg.sv"]
    assert "prim_alert_pkg::" not in dict(prepared.support_files)["uart_public_types_pkg.sv"]
    assert "function automatic uart_public_types_pkg::uart_tl_i_t tl_make_get32(" in dict(
        prepared.support_files
    )["uart_public_tlul_pkg.sv"]
    assert "function automatic uart_public_types_pkg::uart_tl_i_t tl_make_putpartial32(" in dict(
        prepared.support_files
    )["uart_public_tlul_pkg.sv"]
    assert "function automatic uart_public_types_pkg::uart_tl_i_t tl_with_user(" in dict(
        prepared.support_files
    )["uart_public_tlul_pkg.sv"]
    assert "function automatic logic [2:0] tl_param(input uart_public_types_pkg::uart_tl_i_t req);" in dict(
        prepared.support_files
    )["uart_public_tlul_pkg.sv"]
    assert "function automatic logic [7:0] tl_rsp_source(input uart_public_types_pkg::uart_tl_o_t rsp);" in dict(
        prepared.support_files
    )["uart_public_tlul_pkg.sv"]
    assert "function automatic logic [6:0] tl_rsp_rsp_intg(input uart_public_types_pkg::uart_tl_o_t rsp);" in dict(
        prepared.support_files
    )["uart_public_tlul_pkg.sv"]
    assert "localparam logic [31:0] ALERT_TEST_OFFSET = 32'h00000000;" in dict(
        prepared.support_files
    )["uart_public_regs_pkg.sv"]
    assert "localparam int unsigned ALERT_TEST_FATAL_FAULT_LSB = 0;" in dict(
        prepared.support_files
    )["uart_public_regs_pkg.sv"]
    assert "localparam logic [31:0] CTRL_OFFSET = 32'h00000004;" in dict(
        prepared.support_files
    )["uart_public_regs_pkg.sv"]
    assert "localparam int unsigned CTRL_TX_LSB = 0;" in dict(prepared.support_files)[
        "uart_public_regs_pkg.sv"
    ]
    assert prepared.hidden_metadata["profile"] == "opentitan_self_contained_v1"
    assert prepared.hidden_metadata["native_interface"]["ports"][1]["width"] == "tlul_pkg::tl_h2d_t"
    assert prepared.hidden_metadata["projection"]["support_files"] == [
        "uart_public_types_pkg.sv",
        "uart_public_tlul_pkg.sv",
        "uart_public_regs_pkg.sv",
    ]


def test_materialize_public_interface_sv_writes_support_package_when_requested(tmp_path: Path) -> None:
    interface = normalize_public_interface_contract(
        {
            "top_module": "uart",
            "declared_module_name": "uart",
            "ports": [
                {
                    "name": "tl_i",
                    "direction": "input",
                    "width": "uart_public_types_pkg::uart_tl_i_t",
                },
            ],
            "parameters": [],
        },
        candidate_top_module="uart",
    )

    written = materialize_public_interface_sv(
        tmp_path,
        interface,
        support_files=(
            (
                "uart_public_types_pkg.sv",
                "package uart_public_types_pkg;\n"
                "  typedef logic [108:0] uart_tl_i_t;\n"
                "endpackage\n",
            ),
        ),
    )

    assert (written.interface_dir / "uart_public_types_pkg.sv").read_text().startswith(
        "package uart_public_types_pkg;"
    )
    assert "`include \"uart_public_types_pkg.sv\"" in written.sv_path.read_text()
