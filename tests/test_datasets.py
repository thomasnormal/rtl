from pathlib import Path

import pytest

from rtl_training.datasets import (
    DatasetManifest,
    discover_rtllm_tasks,
    discover_verilog_eval_tasks,
)

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_anchor_counts_and_order() -> None:
    manifest = DatasetManifest.load(ROOT / "configs" / "datasets.json")
    assert manifest.ordered_recommendations()[0].name == "rtllm_v1_1"
    assert manifest.total_example_count("anchor_seed") == 235
    assert manifest.by_name("asserteval").has_formal_oracle is True
    assert manifest.by_name("riscv_hardware_specs").status == "ready"
    assert manifest.by_name("riscv_hardware_specs").example_count == 2
    assert manifest.by_name("riscv_hardware_specs").has_testbench is False
    assert manifest.by_name("riscv_hardware_specs").has_gold_rtl is False
    assert manifest.by_name("riscv_hardware_specs").default_tier == "large"
    assert manifest.by_name("opentitan").default_tier == "medium"
    assert manifest.by_name("opentitan").status == "ready"
    assert manifest.by_name("opentitan").example_count == 9
    assert manifest.by_name("cva6_user_manual").default_tier == "large"
    assert manifest.by_name("jedec_ddr6_private").default_tier == "industrial"


def test_manifest_rejects_unknown_dataset_names() -> None:
    manifest = DatasetManifest.load(ROOT / "configs" / "datasets.json")
    assert manifest.validate_dataset_names(["rtllm_v1_1", "missing"]) == ("missing",)


def test_discover_rtllm_tasks_recurses_and_matches_verified_variants(tmp_path: Path) -> None:
    task_dir = tmp_path / "Arithmetic" / "Adder" / "adder_8bit"
    task_dir.mkdir(parents=True)
    (task_dir / "design_description.txt").write_text("spec")
    (task_dir / "verified_adder_8bit.v").write_text("module adder_8bit; endmodule")
    (task_dir / "testbench.v").write_text("module testbench; endmodule")
    (tmp_path / "_chatgpt4" / "t1").mkdir(parents=True)
    (tmp_path / "_chatgpt4" / "t1" / "adder_8bit.v").write_text("module garbage; endmodule")
    tasks = discover_rtllm_tasks(tmp_path, dataset_name="rtllm_v1_1")
    assert [task.task_id for task in tasks] == ["adder_8bit"]
    assert tasks[0].dataset_name == "rtllm_v1_1"
    assert tasks[0].gold_rtl_path is not None
    assert tasks[0].gold_rtl_path.name == "verified_adder_8bit.v"
    assert tasks[0].source_rel_dir.as_posix() == "Arithmetic/Adder/adder_8bit"


def test_discover_verilog_eval_groups_prompt_ref_and_test(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset_spec-to-rtl"
    dataset_dir.mkdir(parents=True)
    (dataset_dir / "Prob001_zero_prompt.txt").write_text("Implement zero.\n")
    (dataset_dir / "Prob001_zero_ref.sv").write_text("module RefModule; endmodule\n")
    (dataset_dir / "Prob001_zero_test.sv").write_text("module tb; endmodule\n")

    tasks = discover_verilog_eval_tasks(
        tmp_path,
        dataset_name="verilogeval_v2_spec_to_rtl",
    )

    assert [task.task_id for task in tasks] == ["Prob001_zero"]
    assert tasks[0].gold_rtl_path is not None
    assert tasks[0].testbench_path is not None
    assert tasks[0].source_rel_dir.as_posix() == "dataset_spec-to-rtl/Prob001_zero"


def test_discover_verilog_eval_rejects_incomplete_tasks(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset_spec-to-rtl"
    dataset_dir.mkdir(parents=True)
    (dataset_dir / "Prob001_zero_prompt.txt").write_text("Implement zero.\n")
    (dataset_dir / "Prob001_zero_ref.sv").write_text("module RefModule; endmodule\n")

    with pytest.raises(ValueError):
        discover_verilog_eval_tasks(
            tmp_path,
            dataset_name="verilogeval_v2_spec_to_rtl",
        )
