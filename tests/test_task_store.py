import json
from pathlib import Path

import pytest

from rtl_training.task_store import (
    load_stored_task,
    store_generic_task,
    store_opentitan_ip_docs_tasks,
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
    assert public_metadata["candidate_top_module"] == "adder_8bit"
    assert public_metadata["spec"] == "spec/"


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

    assert public_metadata["deliverables"]["rtl"] == "submission/"
    assert public_metadata["interface"]["top_module"] == "RAM"
    assert public_metadata["interface"]["declared_module_name"] == "RAM"
    assert public_metadata["interface"]["inputs"] == [
        {"name": "clk", "description": "Clock signal."},
        {"name": "write_en", "description": "Write enable."},
    ]
    assert public_metadata["interface"]["outputs"] == [
        {"name": "read_data", "description": "Read data output."},
    ]
    assert public_metadata["interface"]["parameters"] == [
        {"name": "WIDTH", "value": "6"},
        {"name": "DEPTH", "value": "8"},
    ]


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
    public_metadata = json.loads((written[0] / "public" / "task.json").read_text())

    assert public_metadata["interface"]["inputs"] == [
        {"name": "clk", "description": "Clock signal."},
        {"name": "rst_n", "description": "Reset signal."},
        {"name": "data_in", "description": "One-bit input signal."},
    ]
    assert public_metadata["interface"]["outputs"] == [
        {"name": "data_out", "description": "Pulse output."},
    ]


def test_store_rtllm_tasks_uses_curated_interface_manifest_for_rtllm_v1_1(tmp_path: Path) -> None:
    source_root = tmp_path / "RTLLM"
    task_dir = source_root / "Memory" / "RAM" / "RAM"
    task_dir.mkdir(parents=True)
    (task_dir / "design_description.txt").write_text("intentionally unstructured prose")
    (task_dir / "verified_RAM.v").write_text("module verified_RAM; endmodule\n")
    (task_dir / "testbench.v").write_text("module testbench; endmodule\n")

    output_root = tmp_path / "task_store"
    written = store_rtllm_tasks(source_root, output_root, dataset_name="rtllm_v1_1")
    public_metadata = json.loads((written[0] / "public" / "task.json").read_text())

    assert public_metadata["candidate_top_module"] == "RAM"
    assert public_metadata["interface"]["top_module"] == "RAM"
    assert public_metadata["interface"]["notes"] == [
        "The oracle uses 8-bit read/write addresses and 6-bit data.",
        "The published prose about DEPTH is inconsistent with the hidden oracle; follow this interface.",
    ]
    assert public_metadata["interface"]["ports"] == [
        {"name": "clk", "direction": "input"},
        {"name": "rst_n", "direction": "input"},
        {"name": "write_en", "direction": "input"},
        {"name": "write_addr", "direction": "input", "width": "[7:0]"},
        {"name": "write_data", "direction": "input", "width": "[5:0]"},
        {"name": "read_en", "direction": "input"},
        {"name": "read_addr", "direction": "input", "width": "[7:0]"},
        {"name": "read_data", "direction": "output", "width": "[5:0]"},
    ]


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
    public_metadata = json.loads((written[0] / "public" / "task.json").read_text())

    assert public_metadata["interface"]["top_module"] == "div_16bit"
    assert public_metadata["interface"]["ports"] == [
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
    assert public["spec"] == "spec/"
    assert public["candidate_top_module"] == "adder_4bit"


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
        "dma",
        "i2c",
        "spi_host",
        "sysrst_ctrl",
        "uart",
    ]

    uart_task = load_stored_task(tmp_path / "task_store" / "opentitan_ip_docs" / "uart")
    assert uart_task.tier == "medium"
    assert (uart_task.spec_dir / "README.md").read_text().startswith("# UART HWIP Technical Specification")
    assert (uart_task.spec_dir / "doc" / "theory_of_operation.md").exists()
    assert (uart_task.spec_dir / "dv" / "README.md").exists()
    assert not (uart_task.spec_dir / "spec.md").exists()

    public_metadata = json.loads(uart_task.public_task_path.read_text())
    assert public_metadata["candidate_top_module"] == "uart"
    assert public_metadata["interface"]["top_module"] == "uart"
    assert public_metadata["interface"]["inputs"][0] == {
        "name": "clk_i",
        "direction": "input",
        "width": "logic",
    }

    task_metadata = json.loads((uart_task.root / "task.json").read_text())
    assert task_metadata["source"]["origin"] == "curated_task_pack"
    assert task_metadata["source"]["spec_subdir"] == "uart"
    assert "hw/ip/uart/README.md" in task_metadata["source"]["source_docs"]
    assert task_metadata["source"]["source_root"] == str(Path("~/opentitan").expanduser().resolve())


def test_load_stored_task_backward_compat_old_spec_format(tmp_path: Path) -> None:
    """Old format: spec points to a single file, not a directory."""
    task_root = tmp_path / "old_task"
    public_dir = task_root / "public"
    public_dir.mkdir(parents=True)
    (public_dir / "spec.txt").write_text("old spec")
    (public_dir / "task.json").write_text(json.dumps({"dataset_name": "old", "task_id": "t1"}) + "\n")
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
    assert (task.spec_dir / "spec.txt").read_text() == "old spec"
