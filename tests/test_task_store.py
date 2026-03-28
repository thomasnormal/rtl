import json
from pathlib import Path

import pytest

from rtl_training.interface_contracts import discover_public_interface_spec, read_public_top_module
from rtl_training.micro_arch_contracts import discover_micro_arch_interface_spec
from rtl_training.shared_sources import SharedSourceRegistry
from rtl_training.task_store import (
    load_stored_task,
    store_generic_task,
    store_opentitan_ip_docs_tasks,
    store_riscv_hardware_specs_tasks,
    store_rtllm_tasks,
    store_verilog_eval_tasks,
)

def test_store_rtllm_tasks_separates_public_inputs_from_hidden_oracle(tmp_path: Path) -> None:
    source_root = tmp_path / "RTLLM"
    task_dir = source_root / "Arithmetic" / "Adder" / "adder_8bit"
    task_dir.mkdir(parents=True)
    (task_dir / "design_description.txt").write_text("8-bit adder")
    (task_dir / "verified_adder_8bit.v").write_text("module verified_adder_8bit; endmodule\n")
    (task_dir / "testbench.v").write_text("module testbench; endmodule\n")

    output_root = tmp_path / "task_store"
    written = store_rtllm_tasks(source_root, output_root, dataset_name="rtllm_v2_0")
    task = load_stored_task(written[0])

    assert (task.spec_dir / "spec.txt").read_text() == "8-bit adder"
    assert task.public_dir == written[0] / "public"
    assert not (task.public_dir / "gold_rtl.v").exists()
    assert not (task.public_dir / "testbench.v").exists()
    assert task.oracle is not None
    assert task.oracle.gold_rtl_path.read_text() == "module verified_adder_8bit; endmodule\n"
    assert task.oracle.testbench_path.read_text() == "module testbench; endmodule\n"
    assert task.oracle.requires_reference_rtl is False
    assert task.oracle.support_files == ()

    public_metadata = json.loads(task.public_task_path.read_text())
    assert public_metadata["deliverables"]["rtl"] == "submission/"
    assert task.public_top_module == "adder_8bit"
    assert read_public_top_module(task.public_task_path) == "adder_8bit"


def test_store_rtllm_tasks_copies_hidden_support_files_and_selects_verified_top(tmp_path: Path) -> None:
    source_root = tmp_path / "RTLLM"
    task_dir = source_root / "FIFO" / "Async" / "asyn_fifo"
    task_dir.mkdir(parents=True)
    (task_dir / "design_description.txt").write_text("async fifo")
    (task_dir / "verified_asyn_fifo.v").write_text(
        "module dual_port_RAM; endmodule\n"
        "module verified_asyn_fifo(input logic clk); endmodule\n"
    )
    (task_dir / "testbench.v").write_text("module testbench; endmodule\n")
    (task_dir / "wfull.txt").write_text("1\n")
    (task_dir / "rempty.txt").write_text("0\n")

    output_root = tmp_path / "task_store"
    written = store_rtllm_tasks(source_root, output_root, dataset_name="rtllm_v1_1")
    task = load_stored_task(written[0])

    assert task.oracle is not None
    assert task.oracle.reference_top_module == "verified_asyn_fifo"
    assert sorted(path.name for path in task.oracle.support_files) == ["rempty.txt", "wfull.txt"]
    assert all(path.read_text().strip() in {"0", "1"} for path in task.oracle.support_files)


def test_store_rtllm_tasks_extracts_public_interface_contract_from_structured_spec(tmp_path: Path) -> None:
    source_root = tmp_path / "RTLLM"
    task_dir = source_root / "Memory" / "RAM" / "RAM"
    task_dir.mkdir(parents=True)
    (task_dir / "design_description.txt").write_text(
        "\n".join(
            [
                "Module name:",
                "    RAM",
                "Input ports:",
                "    clk: Clock signal.",
                "    write_en: Write enable.",
                "Output ports:",
                "    read_data: Read data output.",
                "Parameter:",
                "    WIDTH = 6;",
                "    DEPTH = 8;",
                "",
            ]
        )
    )
    (task_dir / "verified_RAM.v").write_text("module verified_RAM; endmodule\n")
    (task_dir / "testbench.v").write_text("module testbench; endmodule\n")

    output_root = tmp_path / "task_store"
    written = store_rtllm_tasks(source_root, output_root, dataset_name="rtllm_v2_0")
    public_metadata = json.loads((written[0] / "public" / "task.json").read_text())
    public_interface = discover_public_interface_spec((written[0] / "public" / "spec"))

    assert public_metadata["deliverables"]["rtl"] == "submission/"
    assert read_public_top_module(written[0] / "public" / "task.json") == "RAM"
    assert public_interface is not None
    assert list(public_interface.ports) == [
        {"name": "clk", "direction": "input"},
        {"name": "write_en", "direction": "input"},
        {"name": "read_data", "direction": "output"},
    ]
    interface_sv = (written[0] / "public" / "spec" / "interface" / "RAM_public_if.sv").read_text()
    assert "parameter WIDTH = 6" in interface_sv
    assert "parameter DEPTH = 8" in interface_sv
    assert "logic clk; // Clock signal." in interface_sv
    assert "logic write_en; // Write enable." in interface_sv
    assert "logic read_data; // Read data output." in interface_sv


def test_store_rtllm_tasks_extracts_interface_from_fullwidth_colon_sections(tmp_path: Path) -> None:
    source_root = tmp_path / "RTLLM"
    task_dir = source_root / "Logic" / "Detector" / "pulse_detect"
    task_dir.mkdir(parents=True)
    (task_dir / "design_description.txt").write_text(
        "\n".join(
            [
                "Module name:",
                "    pulse_detect",
                "Input ports：",
                "    clk: Clock signal.",
                "    rst_n: Reset signal.",
                "    data_in: One-bit input signal.",
                "Output ports：",
                "    data_out: Pulse output.",
                "Implementation:",
                "    Detect 0->1->0 patterns.",
                "",
            ]
        )
    )
    (task_dir / "verified_pulse_detect.v").write_text("module verified_pulse_detect; endmodule\n")
    (task_dir / "testbench.v").write_text("module testbench; endmodule\n")

    output_root = tmp_path / "task_store"
    written = store_rtllm_tasks(source_root, output_root, dataset_name="rtllm_v2_0")
    public_if_text = (written[0] / "public" / "spec" / "interface" / "pulse_detect_public_if.sv").read_text()

    assert "logic clk; // Clock signal." in public_if_text
    assert "logic rst_n; // Reset signal." in public_if_text
    assert "logic data_in; // One-bit input signal." in public_if_text
    assert "logic data_out; // Pulse output." in public_if_text


def test_store_rtllm_tasks_uses_curated_interface_manifest_for_rtllm_v1_1(tmp_path: Path) -> None:
    source_root = tmp_path / "RTLLM"
    task_dir = source_root / "Memory" / "RAM" / "RAM"
    task_dir.mkdir(parents=True)
    (task_dir / "design_description.txt").write_text("intentionally unstructured prose")
    (task_dir / "verified_RAM.v").write_text("module verified_RAM; endmodule\n")
    (task_dir / "testbench.v").write_text("module testbench; endmodule\n")

    output_root = tmp_path / "task_store"
    written = store_rtllm_tasks(source_root, output_root, dataset_name="rtllm_v1_1")
    public_if = discover_public_interface_spec(written[0] / "public" / "spec")
    sv_contract = written[0] / "public" / "spec" / "interface" / "RAM_public_if.sv"

    assert read_public_top_module(written[0] / "public" / "task.json") == "RAM"
    assert public_if is not None
    assert list(public_if.ports) == [
        {"name": "clk", "direction": "input"},
        {"name": "rst_n", "direction": "input"},
        {"name": "write_en", "direction": "input"},
        {"name": "write_addr", "direction": "input", "width": "[7:0]"},
        {"name": "write_data", "direction": "input", "width": "[5:0]"},
        {"name": "read_en", "direction": "input"},
        {"name": "read_addr", "direction": "input", "width": "[7:0]"},
        {"name": "read_data", "direction": "output", "width": "[5:0]"},
    ]
    assert sv_contract.exists()
    assert "logic [7:0] write_addr;" in sv_contract.read_text()
    assert "modport dut (" in sv_contract.read_text()
    assert "follow this interface" not in json.loads((written[0] / "public" / "task.json").read_text())


def test_store_rtllm_tasks_requires_curated_manifest_for_rtllm_v1_1(tmp_path: Path) -> None:
    source_root = tmp_path / "RTLLM"
    task_dir = source_root / "Misc" / "mystery"
    task_dir.mkdir(parents=True)
    (task_dir / "design_description.txt").write_text("mystery task")
    (task_dir / "verified_mystery.v").write_text("module verified_mystery; endmodule\n")
    (task_dir / "testbench.v").write_text("module testbench; endmodule\n")

    with pytest.raises(ValueError, match="missing curated interface manifest entry"):
        store_rtllm_tasks(source_root, tmp_path / "task_store", dataset_name="rtllm_v1_1")


def test_store_rtllm_tasks_skips_known_invalid_anchor_tasks_by_default(tmp_path: Path) -> None:
    source_root = tmp_path / "RTLLM"
    task_dir = source_root / "Arithmetic" / "Divider" / "div_16bit"
    task_dir.mkdir(parents=True)
    (task_dir / "design_description.txt").write_text("broken divider benchmark")
    (task_dir / "verified_div_16bit.v").write_text("module verified_div_16bit; endmodule\n")
    (task_dir / "testbench.v").write_text("module testbench; endmodule\n")

    output_root = tmp_path / "task_store"
    written = store_rtllm_tasks(source_root, output_root, dataset_name="rtllm_v1_1")

    assert written == ()
    assert not (output_root / "rtllm_v1_1" / "div_16bit").exists()

    written = store_rtllm_tasks(
        source_root,
        output_root,
        dataset_name="rtllm_v1_1",
        include_invalid=True,
    )
    public_interface = discover_public_interface_spec(written[0] / "public" / "spec")

    assert read_public_top_module(written[0] / "public" / "task.json") == "div_16bit"
    assert public_interface is not None
    assert list(public_interface.ports) == [
        {"name": "A", "direction": "input", "width": "[15:0]"},
        {"name": "B", "direction": "input", "width": "[7:0]"},
        {"name": "result", "direction": "output", "width": "[15:0]"},
        {"name": "odd", "direction": "output", "width": "[15:0]"},
    ]


def test_store_verilog_eval_tasks_keeps_reference_model_hidden(tmp_path: Path) -> None:
    source_root = tmp_path / "verilog-eval"
    dataset_dir = source_root / "dataset_spec-to-rtl"
    dataset_dir.mkdir(parents=True)
    (dataset_dir / "Prob001_zero_prompt.txt").write_text("Implement zero.\n")
    (dataset_dir / "Prob001_zero_ref.sv").write_text("module RefModule; endmodule\n")
    (dataset_dir / "Prob001_zero_test.sv").write_text("module tb; endmodule\n")

    output_root = tmp_path / "task_store"
    written = store_verilog_eval_tasks(
        source_root,
        output_root,
        dataset_name="verilogeval_v2_spec_to_rtl",
    )
    task = load_stored_task(written[0])

    assert task.oracle is not None
    assert task.oracle.requires_reference_rtl is True
    assert task.oracle.reference_top_module == "RefModule"
    assert task.oracle.candidate_top_module == "TopModule"
    assert not any(path.name.startswith("gold_rtl") for path in task.public_dir.iterdir())
    assert not any(path.name.startswith("testbench") for path in task.public_dir.iterdir())


def test_store_rtllm_tasks_writes_tier_when_provided(tmp_path: Path) -> None:
    source_root = tmp_path / "RTLLM"
    task_dir = source_root / "Arithmetic" / "Adder" / "adder_8bit"
    task_dir.mkdir(parents=True)
    (task_dir / "design_description.txt").write_text("8-bit adder")
    (task_dir / "verified_adder_8bit.v").write_text("module verified_adder_8bit; endmodule\n")
    (task_dir / "testbench.v").write_text("module testbench; endmodule\n")

    written = store_rtllm_tasks(
        source_root, tmp_path / "task_store", dataset_name="rtllm_v2_0", tier="small"
    )
    task = load_stored_task(written[0])

    assert task.tier == "small"
    public_metadata = json.loads(task.public_task_path.read_text())
    assert public_metadata["tier"] == "small"


def test_store_generic_task_with_text_spec(tmp_path: Path) -> None:
    task_root = store_generic_task(
        output_root=tmp_path / "task_store",
        dataset_name="custom",
        task_id="my_adder",
        spec_source="Design a 4-bit adder.",
        candidate_top_module="adder_4bit",
        tier="micro",
    )
    task = load_stored_task(task_root)

    assert task.tier == "micro"
    assert task.oracle is None
    assert (task.spec_dir / "spec.txt").read_text() == "Design a 4-bit adder."
    public = json.loads(task.public_task_path.read_text())
    assert public["deliverables"]["summary"] == "result/result.json"
    assert task.public_top_module == "adder_4bit"


def test_store_generic_task_with_directory_spec(tmp_path: Path) -> None:
    spec_dir = tmp_path / "my_spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("# DDR5 Controller\n\nDetailed spec.")
    (spec_dir / "timing.png").write_bytes(b"\x89PNG")

    task_root = store_generic_task(
        output_root=tmp_path / "task_store",
        dataset_name="custom",
        task_id="ddr5_ctrl",
        spec_source=spec_dir,
        candidate_top_module="ddr5_ctrl",
        tier="industrial",
    )
    task = load_stored_task(task_root)

    assert task.tier == "industrial"
    assert (task.spec_dir / "spec.md").read_text() == "# DDR5 Controller\n\nDetailed spec."
    assert (task.spec_dir / "timing.png").exists()


def test_store_generic_task_with_oracle(tmp_path: Path) -> None:
    gold = tmp_path / "gold.v"
    gold.write_text("module adder; endmodule\n")
    tb = tmp_path / "tb.v"
    tb.write_text("module testbench; endmodule\n")

    task_root = store_generic_task(
        output_root=tmp_path / "task_store",
        dataset_name="custom",
        task_id="adder",
        spec_source="Simple adder.",
        candidate_top_module="adder",
        gold_rtl_path=gold,
        testbench_path=tb,
    )
    task = load_stored_task(task_root)

    assert task.oracle is not None
    assert task.oracle.candidate_top_module == "adder"


def test_store_generic_task_with_private_sources_keeps_assets_hidden(tmp_path: Path) -> None:
    private_dir = tmp_path / "upstream"
    (private_dir / "rtl").mkdir(parents=True)
    (private_dir / "rtl" / "top.sv").write_text("module top; endmodule\n")
    (private_dir / "dv").mkdir()
    (private_dir / "dv" / "README.md").write_text("dv collateral\n")

    task_root = store_generic_task(
        output_root=tmp_path / "task_store",
        dataset_name="custom",
        task_id="private_assets",
        spec_source="public spec",
        candidate_top_module="top",
        private_sources=(private_dir / "rtl", private_dir / "dv"),
    )
    task = load_stored_task(task_root)

    assert task.private_dir == task_root / "private"
    assert (task.private_dir / "rtl" / "top.sv").exists()
    assert (task.private_dir / "dv" / "README.md").exists()
    assert not (task.public_dir / "rtl").exists()
    metadata = json.loads((task_root / "task.json").read_text())
    assert metadata["private"]["assets"] == ["private/rtl", "private/dv"]


def test_store_generic_task_preserves_source_metadata(tmp_path: Path) -> None:
    task_root = store_generic_task(
        output_root=tmp_path / "task_store",
        dataset_name="custom",
        task_id="meta_task",
        spec_source="metadata demo",
        candidate_top_module="meta_task",
        source_metadata={"origin": "manual", "source_docs": ["spec.md"]},
    )
    metadata = json.loads((task_root / "task.json").read_text())

    assert metadata["source"] == {"origin": "manual", "source_docs": ["spec.md"]}


def test_store_generic_task_overwrite_removes_stale_spec_files(tmp_path: Path) -> None:
    first_spec_dir = tmp_path / "spec_a"
    first_spec_dir.mkdir()
    (first_spec_dir / "spec.md").write_text("old summary")

    second_spec_dir = tmp_path / "spec_b"
    (second_spec_dir / "doc").mkdir(parents=True)
    (second_spec_dir / "README.md").write_text("upstream readme")
    (second_spec_dir / "doc" / "theory_of_operation.md").write_text("upstream theory")

    output_root = tmp_path / "task_store"
    store_generic_task(
        output_root=output_root,
        dataset_name="custom",
        task_id="overwrite_me",
        spec_source=first_spec_dir,
        candidate_top_module="overwrite_me",
    )
    task_root = store_generic_task(
        output_root=output_root,
        dataset_name="custom",
        task_id="overwrite_me",
        spec_source=second_spec_dir,
        candidate_top_module="overwrite_me",
    )

    spec_dir = task_root / "public" / "spec"
    assert (spec_dir / "README.md").read_text() == "upstream readme"
    assert (spec_dir / "doc" / "theory_of_operation.md").read_text() == "upstream theory"
    assert not (spec_dir / "spec.md").exists()


def test_store_opentitan_ip_docs_tasks_materializes_curated_specs(tmp_path: Path) -> None:
    written = store_opentitan_ip_docs_tasks(
        tmp_path / "task_store",
        source_root="~/opentitan",
    )

    assert sorted(path.name for path in written) == [
        "adc_ctrl",
        "aon_timer",
        "dma",
        "i2c",
        "pattgen",
        "rv_timer",
        "spi_host",
        "sysrst_ctrl",
        "uart",
    ]

    uart_task = load_stored_task(tmp_path / "task_store" / "opentitan_ip_docs" / "uart")
    assert uart_task.tier == "medium"
    uart_readme = (uart_task.spec_dir / "README.md").read_text()
    assert uart_readme.startswith("# UART Specification")
    assert "OpenTitan" not in uart_readme
    assert (uart_task.spec_dir / "doc" / "theory_of_operation.md").exists()
    assert (uart_task.spec_dir / "dv" / "README.md").exists()
    assert not any((uart_task.spec_dir / "dv").glob("*_sim_cfg.hjson"))
    assert not any((uart_task.spec_dir / "data").glob("*testplan*.hjson"))
    assert not (uart_task.spec_dir / "spec.md").exists()

    public_metadata = json.loads(uart_task.public_task_path.read_text())
    assert public_metadata == {
        "dataset_name": "opentitan_ip_docs",
        "deliverables": {
            "rtl": "submission/",
            "summary": "result/result.json",
        },
        "task_id": "uart",
        "top_module": "uart",
        "tier": "medium",
    }
    assert uart_task.public_top_module == "uart"
    uart_public_if = discover_public_interface_spec(uart_task.spec_dir)
    assert uart_public_if is not None
    assert list(uart_public_if.ports)[0] == {
        "name": "clk_i",
        "direction": "input",
    }
    assert list(uart_public_if.ports)[2] == {
        "name": "tl_i",
        "direction": "input",
        "width": "uart_public_types_pkg::uart_tl_i_t",
    }
    assert (uart_task.spec_dir / "interface" / "uart_public_if.sv").exists()
    public_if_text = (uart_task.spec_dir / "interface" / "uart_public_if.sv").read_text()
    assert "tlul_pkg::" not in public_if_text
    assert "`include \"uart_public_types_pkg.sv\"" in public_if_text
    assert "`include \"uart_public_tlul_pkg.sv\"" in public_if_text
    assert "`include \"uart_public_regs_pkg.sv\"" in public_if_text
    public_pkg_text = (uart_task.spec_dir / "interface" / "uart_public_types_pkg.sv").read_text()
    assert "typedef logic [108:0] uart_tl_i_t;" in public_pkg_text
    assert "typedef logic [65:0] uart_tl_o_t;" in public_pkg_text
    assert "tlul_pkg::" not in public_pkg_text
    assert "prim_alert_pkg::" not in public_pkg_text
    tlul_pkg_text = (uart_task.spec_dir / "interface" / "uart_public_tlul_pkg.sv").read_text()
    assert "function automatic uart_public_types_pkg::uart_tl_i_t tl_make_get32(" in tlul_pkg_text
    regs_pkg_text = (uart_task.spec_dir / "interface" / "uart_public_regs_pkg.sv").read_text()
    assert "localparam logic [31:0] ALERT_TEST_OFFSET = 32'h00000000;" in regs_pkg_text
    assert "localparam int unsigned ALERT_TEST_FATAL_FAULT_LSB = 0;" in regs_pkg_text
    assert "localparam logic [31:0] CTRL_OFFSET = 32'h00000004;" in regs_pkg_text

    task_metadata = json.loads((uart_task.root / "task.json").read_text())
    assert task_metadata["source"]["origin"] == "curated_task_pack"
    assert task_metadata["source"]["spec_subdir"] == "uart"
    assert "hw/ip/uart/README.md" in task_metadata["source"]["source_docs"]
    assert task_metadata["source"]["source_root"].startswith(str(tmp_path.resolve()))
    assert "/shared_sources/bundles/opentitan_ip_docs-" in task_metadata["source"]["source_root"]
    assert task_metadata["source"]["source_checkout_root"] == str(
        Path("~/opentitan").expanduser().resolve()
    )
    assert task_metadata["source"]["private_source_dirs"] == [
        "hw/ip/uart/rtl",
        "hw/ip/uart/dv",
    ]
    assert task_metadata["source"]["private_source_mode"] == "shared_bundle"
    assert task_metadata["source"]["public_interface_internal"]["profile"] == (
        "opentitan_self_contained_v1"
    )
    assert (
        task_metadata["source"]["public_interface_internal"]["projection"]["ports"][2]["native_type"]
        == "tlul_pkg::tl_h2d_t"
    )
    assert task_metadata["source"]["public_interface_internal"]["projection"]["support_files"] == [
        "uart_public_types_pkg.sv",
        "uart_public_tlul_pkg.sv",
        "uart_public_regs_pkg.sv",
    ]
    assert task_metadata["oracle"]["kind"] == "opentitan_dvsim"
    assert task_metadata["oracle"]["cfg"] == "hw/ip/uart/dv/uart_sim_cfg.hjson"
    assert task_metadata["oracle"]["test"] == "uart_smoke"
    assert task_metadata["oracle"]["golden_rtl_dir"] == "golden_rtl"
    assert task_metadata["oracle"]["overlay_rel_dir"] == "hw/ip/uart/rtl"
    assert task_metadata["oracle"]["repo_overlay_dir"] == "repo_overlay"
    assert uart_task.private_dir is None
    assert uart_task.shared_private_ref is not None
    assert uart_task.shared_private_ref.subpaths == ("hw/ip/uart/rtl", "hw/ip/uart/dv")
    assert (uart_task.root / "oracle" / "golden_rtl" / "uart.sv").exists()
    assert (uart_task.root / "oracle" / "golden_rtl" / "uart_core.sv").exists()
    assert (uart_task.root / "oracle" / "repo_overlay" / "hw" / "ip" / "uart" / "dv" / "tb" / "tb.sv").exists()
    assert (
        uart_task.root / "oracle" / "repo_overlay" / "hw" / "ip" / "uart" / "dv" / "compat" / "uart_compat_bind.sv"
    ).exists()
    registry = SharedSourceRegistry.load(uart_task.shared_private_ref.registry_path)
    bundle = registry.by_id(uart_task.shared_private_ref.bundle_id)
    assert bundle.root == Path(task_metadata["source"]["source_root"]).resolve()
    assert bundle.git_commit is not None
    assert bundle.git_dirty is False
    assert uart_task.shared_private_ref.resolve_paths() == (
        bundle.root / "hw/ip/uart/rtl",
        bundle.root / "hw/ip/uart/dv",
    )

    adc_task = load_stored_task(tmp_path / "task_store" / "opentitan_ip_docs" / "adc_ctrl")
    adc_public_if = discover_public_interface_spec(adc_task.spec_dir)
    assert adc_public_if is not None
    assert list(adc_public_if.ports)[6] == {
        "name": "adc_i",
        "direction": "input",
        "width": "adc_ctrl_public_types_pkg::adc_ctrl_adc_i_t",
    }
    adc_public_pkg_text = (adc_task.spec_dir / "interface" / "adc_ctrl_public_types_pkg.sv").read_text()
    assert "typedef logic [2:0] adc_ctrl_adc_o_t;" in adc_public_pkg_text
    assert "typedef logic [10:0] adc_ctrl_adc_i_t;" in adc_public_pkg_text
    adc_task_metadata = json.loads((adc_task.root / "task.json").read_text())
    assert adc_task_metadata["oracle"]["test"] == "adc_ctrl_smoke"

    aon_timer_task = load_stored_task(tmp_path / "task_store" / "opentitan_ip_docs" / "aon_timer")
    assert json.loads((aon_timer_task.root / "task.json").read_text())["oracle"]["test"] == "aon_timer_smoke"

    pattgen_task = load_stored_task(tmp_path / "task_store" / "opentitan_ip_docs" / "pattgen")
    assert json.loads((pattgen_task.root / "task.json").read_text())["oracle"]["test"] == "pattgen_smoke"

    rv_timer_task = load_stored_task(tmp_path / "task_store" / "opentitan_ip_docs" / "rv_timer")
    rv_timer_task_metadata = json.loads((rv_timer_task.root / "task.json").read_text())
    assert rv_timer_task_metadata["oracle"]["test"] == "rv_timer_random"
    assert rv_timer_task_metadata["oracle"]["cfg"] == "hw/ip/rv_timer/dv/rv_timer_sim_cfg.hjson"
    assert (rv_timer_task.spec_dir / "micro_arch" / "README.md").exists()
    rv_timer_micro_arch_if = (rv_timer_task.spec_dir / "micro_arch" / "rv_timer_micro_arch_if.sv").read_text()
    assert "modport dut (" in rv_timer_micro_arch_if
    assert "modport tb (" in rv_timer_micro_arch_if
    assert "tl_intg_error_pulse" in rv_timer_micro_arch_if
    rv_timer_micro_arch_checker = (
        rv_timer_task.spec_dir / "micro_arch" / "rv_timer_micro_arch_checker.sv"
    ).read_text()
    assert "p_error_pulse_drives_alert" in rv_timer_micro_arch_checker

    dma_task = load_stored_task(tmp_path / "task_store" / "opentitan_ip_docs" / "dma")
    dma_task_metadata = json.loads((dma_task.root / "task.json").read_text())
    assert dma_task_metadata["oracle"]["kind"] == "opentitan_dvsim"
    assert dma_task_metadata["oracle"]["cfg"] == "hw/ip/dma/dv/dma_sim_cfg.hjson"
    assert dma_task_metadata["oracle"]["test"] == "dma_generic_smoke"
    assert dma_task_metadata["oracle"]["golden_rtl_dir"] == "golden_rtl"
    assert dma_task_metadata["oracle"]["overlay_rel_dir"] == "hw/ip/dma/rtl"
    assert (dma_task.root / "oracle" / "golden_rtl" / "dma.sv").exists()

    sysrst_ctrl_task = load_stored_task(tmp_path / "task_store" / "opentitan_ip_docs" / "sysrst_ctrl")
    sysrst_ctrl_task_metadata = json.loads((sysrst_ctrl_task.root / "task.json").read_text())
    assert sysrst_ctrl_task_metadata["oracle"]["kind"] == "opentitan_dvsim"
    assert (
        sysrst_ctrl_task_metadata["oracle"]["cfg"]
        == "hw/ip/sysrst_ctrl/dv/sysrst_ctrl_sim_cfg.hjson"
    )
    assert sysrst_ctrl_task_metadata["oracle"]["test"] == "sysrst_ctrl_smoke"
    assert sysrst_ctrl_task_metadata["oracle"]["golden_rtl_dir"] == "golden_rtl"
    assert sysrst_ctrl_task_metadata["oracle"]["overlay_rel_dir"] == "hw/ip/sysrst_ctrl/rtl"
    assert (sysrst_ctrl_task.root / "oracle" / "golden_rtl" / "sysrst_ctrl.sv").exists()


def test_store_riscv_hardware_specs_tasks_materializes_public_pdf_specs(tmp_path: Path) -> None:
    written = store_riscv_hardware_specs_tasks(tmp_path / "task_store")

    assert sorted(path.name for path in written) == [
        "aplic_idc",
        "debug_abstract_command_frontend",
        "imsic_interrupt_file",
    ]

    debug_task = load_stored_task(
        tmp_path / "task_store" / "riscv_hardware_specs" / "debug_abstract_command_frontend"
    )
    assert debug_task.tier == "small"
    assert debug_task.oracle is None
    assert debug_task.private_dir is None
    assert debug_task.shared_private_ref is None
    assert (debug_task.spec_dir / "riscv-debug-spec-v0.13.2.pdf").exists()
    assert (debug_task.spec_dir / "doc" / "README.md").exists()
    assert (debug_task.spec_dir / "doc" / "manifest.json").exists()
    assert (debug_task.spec_dir / "doc" / "registers.md").exists()
    assert (debug_task.spec_dir / "doc" / "05_p033_p040.md").exists()
    assert debug_task.public_top_module == "riscv_debug_abstract_cmd"

    debug_public_metadata = json.loads(debug_task.public_task_path.read_text())
    assert debug_public_metadata == {
        "dataset_name": "riscv_hardware_specs",
        "deliverables": {
            "rtl": "submission/",
            "summary": "result/result.json",
        },
        "task_id": "debug_abstract_command_frontend",
        "top_module": "riscv_debug_abstract_cmd",
        "tier": "small",
    }
    debug_if = (debug_task.spec_dir / "interface" / "riscv_debug_abstract_cmd_public_if.sv").read_text()
    assert "interface riscv_debug_abstract_cmd_public_if;" in debug_if
    assert "logic cmd_start_o;" in debug_if
    assert "logic [2:0] cmd_cmderr_i;" in debug_if
    assert "modport dut (" in debug_if
    assert "normalized `riscv_debug_abstract_cmd` public" in (
        debug_task.spec_dir / "doc" / "registers.md"
    ).read_text()

    debug_task_metadata = json.loads((debug_task.root / "task.json").read_text())
    assert debug_task_metadata["source"]["origin"] == "curated_task_pack"
    assert debug_task_metadata["source"]["spec_subdir"] == "debug_abstract_command_frontend"
    assert debug_task_metadata["source"]["source_docs"] == [
        "https://docs.riscv.org/reference/debug-trace-ras/debug/v0.13.2/_attachments/riscv-debug.pdf",
    ]
    assert "oracle" not in debug_task_metadata

    imsic_task = load_stored_task(
        tmp_path / "task_store" / "riscv_hardware_specs" / "imsic_interrupt_file"
    )
    assert imsic_task.tier == "medium"
    assert imsic_task.oracle is None
    assert (imsic_task.spec_dir / "riscv-interrupts-aia-v1.0.pdf").exists()
    assert (imsic_task.spec_dir / "doc" / "README.md").exists()
    assert (imsic_task.spec_dir / "doc" / "manifest.json").exists()
    assert (imsic_task.spec_dir / "doc" / "registers.md").exists()
    assert (imsic_task.spec_dir / "doc" / "04_p025_p032.md").exists()
    assert (imsic_task.spec_dir / "doc" / "figures" / "02_p009_p016_figure-001.png").exists()
    assert imsic_task.public_top_module == "riscv_imsic"
    assert "eidelivery = 0x4000_0000" in (imsic_task.spec_dir / "doc" / "registers.md").read_text()

    imsic_public_metadata = json.loads(imsic_task.public_task_path.read_text())
    assert imsic_public_metadata == {
        "dataset_name": "riscv_hardware_specs",
        "deliverables": {
            "rtl": "submission/",
            "summary": "result/result.json",
        },
        "task_id": "imsic_interrupt_file",
        "top_module": "riscv_imsic",
        "tier": "medium",
    }
    imsic_if = (imsic_task.spec_dir / "interface" / "riscv_imsic_public_if.sv").read_text()
    assert "interface riscv_imsic_public_if;" in imsic_if
    assert "logic [11:0] req_addr_i;" in imsic_if
    assert "logic [31:0] rsp_rdata_o;" in imsic_if
    assert "modport dut (" in imsic_if

    imsic_task_metadata = json.loads((imsic_task.root / "task.json").read_text())
    assert imsic_task_metadata["source"]["origin"] == "curated_task_pack"
    assert imsic_task_metadata["source"]["spec_subdir"] == "imsic_interrupt_file"
    assert imsic_task_metadata["source"]["source_docs"] == [
        "https://docs.riscv.org/reference/hardware/aia/_attachments/riscv-interrupts.pdf",
    ]

    aplic_task = load_stored_task(tmp_path / "task_store" / "riscv_hardware_specs" / "aplic_idc")
    assert aplic_task.tier == "small"
    assert aplic_task.oracle is None
    assert (aplic_task.spec_dir / "riscv-interrupts-aia-v1.0.pdf").exists()
    assert (aplic_task.spec_dir / "doc" / "README.md").exists()
    assert (aplic_task.spec_dir / "doc" / "manifest.json").exists()
    assert (aplic_task.spec_dir / "doc" / "registers.md").exists()
    assert (aplic_task.spec_dir / "doc" / "07_p049_p056.md").exists()
    assert aplic_task.public_top_module == "riscv_aplic_idc"

    aplic_public_metadata = json.loads(aplic_task.public_task_path.read_text())
    assert aplic_public_metadata == {
        "dataset_name": "riscv_hardware_specs",
        "deliverables": {
            "rtl": "submission/",
            "summary": "result/result.json",
        },
        "task_id": "aplic_idc",
        "top_module": "riscv_aplic_idc",
        "tier": "small",
    }
    aplic_if = (aplic_task.spec_dir / "interface" / "riscv_aplic_idc_public_if.sv").read_text()
    assert "interface riscv_aplic_idc_public_if;" in aplic_if
    assert "logic [255:0] src_prio_i;" in aplic_if
    assert "logic claim_pulse_o;" in aplic_if
    assert "logic [9:0] claim_id_o;" in aplic_if
    assert "modport dut (" in aplic_if
    assert "models one APLIC interrupt delivery control (IDC) block for one hart" in (
        aplic_task.spec_dir / "doc" / "registers.md"
    ).read_text()

    aplic_task_metadata = json.loads((aplic_task.root / "task.json").read_text())
    assert aplic_task_metadata["source"]["origin"] == "curated_task_pack"
    assert aplic_task_metadata["source"]["spec_subdir"] == "aplic_idc"
    assert aplic_task_metadata["source"]["source_docs"] == [
        "https://docs.riscv.org/reference/hardware/aia/_attachments/riscv-interrupts.pdf",
    ]


def test_store_opentitan_tasks_all_publish_micro_arch_contracts(tmp_path: Path) -> None:
    source_root = Path("~/opentitan").expanduser().resolve()
    written = store_opentitan_ip_docs_tasks(
        tmp_path / "task_store",
        source_root=source_root,
    )

    expected_tasks = {
        "adc_ctrl",
        "aon_timer",
        "dma",
        "i2c",
        "pattgen",
        "rv_timer",
        "spi_host",
        "sysrst_ctrl",
        "uart",
    }
    assert {path.name for path in written} == expected_tasks

    for task_name in sorted(expected_tasks):
        task = load_stored_task(tmp_path / "task_store" / "opentitan_ip_docs" / task_name)
        micro_arch_dir = task.spec_dir / "micro_arch"
        assert micro_arch_dir.is_dir(), task_name
        assert (micro_arch_dir / "README.md").is_file(), task_name
        spec = discover_micro_arch_interface_spec(task.spec_dir)
        assert spec is not None, task_name
        assert spec.interface_name == f"{task_name}_micro_arch_if"
        assert spec.instance_name == f"u_{task_name}_micro_arch_if"
        assert "dut" in spec.modports
        assert {"tb", "mon"} & set(spec.modports)
def test_load_stored_task_backward_compat_old_spec_format(tmp_path: Path) -> None:
    """Old format: spec points to a single file, not a directory."""
    task_root = tmp_path / "old_task"
    public_dir = task_root / "public"
    public_dir.mkdir(parents=True)
    (public_dir / "spec.txt").write_text("old spec")
    (public_dir / "task.json").write_text(
        json.dumps({"dataset_name": "old", "task_id": "t1", "top_module": "legacy_top"}) + "\n"
    )
    (task_root / "task.json").write_text(
        json.dumps({
            "dataset_name": "old",
            "task_id": "t1",
            "public": {
                "directory": "public",
                "spec": "public/spec.txt",
                "task": "public/task.json",
            },
            "source": {},
        })
        + "\n"
    )

    task = load_stored_task(task_root)

    # spec_dir should be the parent of the old spec file
    assert task.spec_dir == task_root / "public"
    assert task.public_top_module == "legacy_top"
    assert (task.spec_dir / "spec.txt").read_text() == "old spec"
