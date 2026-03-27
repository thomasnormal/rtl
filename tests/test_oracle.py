from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from rtl_training.oracle import (
    build_candidate_validation_plan,
    build_gold_selftest_plan,
    judge_simulation_output,
    run_simulation_plan,
)
from rtl_training.task_store import PassCriteria, load_stored_task


def _write_task(
    task_root: Path,
    *,
    requires_reference_rtl: bool,
    candidate_top_module: str = "toy",
    reference_top_module: str = "toy",
    gold_name: str = "gold_rtl.v",
    gold_text: str = "module toy; endmodule\n",
    testbench_name: str = "testbench.v",
    support_files: dict[str, str] | None = None,
) -> None:
    (task_root / "public").mkdir(parents=True)
    (task_root / "oracle" / "sim").mkdir(parents=True)
    (task_root / "oracle" / "support").mkdir(parents=True)
    (task_root / "public" / "spec.txt").write_text("spec\n")
    (task_root / "public" / "task.json").write_text(
        json.dumps(
            {
                "dataset_name": "unit",
                "task_id": "toy",
                "top_module": candidate_top_module,
                "deliverables": {
                    "rtl": "submission/",
                    "summary": "result/result.json",
                },
            },
            indent=2,
        )
        + "\n"
    )
    (task_root / "oracle" / gold_name).write_text(gold_text)
    (task_root / "oracle" / "sim" / testbench_name).write_text("module tb; endmodule\n")
    (task_root / "task.json").write_text(
        json.dumps(
            {
                "dataset_name": "unit",
                "task_id": "toy",
                "public": {
                    "directory": "public",
                    "spec": "public/spec.txt",
                    "task": "public/task.json",
                },
                "oracle": {
                    "kind": "simulation",
                    "testbench": f"oracle/sim/{testbench_name}",
                    "gold_rtl": f"oracle/{gold_name}",
                    "requires_reference_rtl": requires_reference_rtl,
                    "candidate_top_module": candidate_top_module,
                    "reference_top_module": reference_top_module,
                    "pass_criteria": {
                        "success_markers": [],
                        "failure_markers": ["TIMEOUT"],
                        "zero_value_regex": r"Mismatches:\s*(\d+)\s+in\s+\d+\s+samples",
                        "zero_value_group": 1,
                    },
                    "support_files": [] if not support_files else [
                        f"oracle/support/{name}" for name in sorted(support_files)
                    ],
                },
                "source": {},
            },
            indent=2,
        )
        + "\n"
    )
    if support_files:
        for name, text in support_files.items():
            (task_root / "oracle" / "support" / name).write_text(text)


def test_build_candidate_validation_plan_uses_hidden_reference_when_needed(tmp_path: Path) -> None:
    task_root = tmp_path / "task"
    _write_task(
        task_root,
        requires_reference_rtl=True,
        gold_name="gold_rtl.sv",
        testbench_name="testbench.sv",
    )
    task = load_stored_task(task_root)
    candidate = tmp_path / "candidate.sv"
    candidate.write_text("module TopModule; endmodule\n")

    plan = build_candidate_validation_plan(task, candidate, work_root=tmp_path / "work")

    assert task.oracle is not None
    assert tuple(path.name for path in plan.source_files) == ("testbench.sv", "gold_rtl.sv", "candidate.sv")
    assert all(path.is_absolute() for path in plan.source_files)
    # Testbench and gold_rtl are in work_dir; candidates are in work_dir/candidate_src
    assert plan.source_files[0].parent == plan.work_dir
    assert plan.source_files[1].parent == plan.work_dir
    assert plan.source_files[2].parent == plan.work_dir / "candidate_src"


def test_build_gold_selftest_plan_rewrites_reference_top_name(tmp_path: Path) -> None:
    task_root = tmp_path / "task"
    _write_task(
        task_root,
        requires_reference_rtl=False,
        candidate_top_module="adder_8bit",
        reference_top_module="verified_adder_8bit",
        gold_text="module verified_adder_8bit(input logic a, output logic b); endmodule\n",
    )
    task = load_stored_task(task_root)

    plan = build_gold_selftest_plan(task, work_root=tmp_path / "work")

    assert plan.source_files[1].name.endswith("__gold_candidate.v")
    assert "module adder_8bit" in plan.source_files[1].read_text()
    assert "verified_adder_8bit" not in plan.source_files[1].read_text()


def test_build_candidate_validation_plan_stages_support_files_into_sim_workdir(tmp_path: Path) -> None:
    task_root = tmp_path / "task"
    _write_task(
        task_root,
        requires_reference_rtl=False,
        support_files={"reference.dat": "123\n", "tri_gen.txt": "abc\n"},
    )
    task = load_stored_task(task_root)
    candidate = tmp_path / "candidate.sv"
    candidate.write_text("module toy; endmodule\n")

    plan = build_candidate_validation_plan(task, candidate, work_root=tmp_path / "work")

    assert (plan.work_dir / "reference.dat").read_text() == "123\n"
    assert (plan.work_dir / "tri_gen.txt").read_text() == "abc\n"


def test_build_gold_selftest_plan_rejects_reference_oracles(tmp_path: Path) -> None:
    task_root = tmp_path / "task"
    _write_task(task_root, requires_reference_rtl=True)
    task = load_stored_task(task_root)

    with pytest.raises(ValueError):
        build_gold_selftest_plan(task, work_root=tmp_path / "work")


def test_judge_simulation_output_uses_explicit_pass_criteria() -> None:
    criteria = PassCriteria(
        success_markers=("Your Design Passed",),
        failure_markers=("TIMEOUT",),
        zero_value_regex=r"Mismatches:\s*(\d+)\s+in\s+\d+\s+samples",
        zero_value_group=1,
    )

    assert judge_simulation_output(
        returncode=0,
        output_text="Mismatches: 0 in 20 samples\n",
        criteria=criteria,
    )
    assert not judge_simulation_output(
        returncode=0,
        output_text="Mismatches: 3 in 20 samples\n",
        criteria=criteria,
    )
    assert not judge_simulation_output(
        returncode=0,
        output_text="TIMEOUT\nMismatches: 0 in 20 samples\n",
        criteria=criteria,
    )
    assert not judge_simulation_output(
        returncode=0,
        output_text="xrun: *E,FILEMIS\nYour Design Passed\n",
        criteria=criteria,
    )


def test_run_simulation_plan_uses_absolute_paths_for_xrun(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_root = tmp_path / "task"
    _write_task(
        task_root,
        requires_reference_rtl=False,
        candidate_top_module="adder_8bit",
        reference_top_module="verified_adder_8bit",
        gold_text="module verified_adder_8bit; endmodule\n",
    )
    candidate = tmp_path / "candidate.sv"
    candidate.write_text("module adder_8bit; endmodule\n")

    monkeypatch.chdir(tmp_path)
    task = load_stored_task(Path("task"))
    plan = build_candidate_validation_plan(
        task,
        Path("candidate.sv"),
        work_root=Path("runs"),
        preferred_simulator="xrun",
    )
    captured: dict[str, object] = {}

    def fake_run(command, *, cwd, capture_output, text, timeout, check):
        captured["command"] = command
        captured["cwd"] = cwd
        plan.log_path.write_text("Your Design Passed\n")
        return subprocess.CompletedProcess(command, 0, stdout="Mismatches: 0 in 20 samples\n", stderr="")

    monkeypatch.setattr("rtl_training.oracle.subprocess.run", fake_run)

    result = run_simulation_plan(plan, timeout_s=30)

    assert result.passed is True
    assert plan.work_dir.is_absolute()
    assert plan.log_path.is_absolute()
    assert all(path.is_absolute() for path in plan.source_files)
    command = captured["command"]
    assert isinstance(command, tuple)
    assert "-sv" in command
    assert command[5].startswith("/")
    assert command[8].startswith("/")
    assert command[9].startswith("/")
    assert Path(captured["cwd"]) == plan.work_dir


def test_run_simulation_plan_treats_xrun_log_errors_as_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_root = tmp_path / "task"
    _write_task(task_root, requires_reference_rtl=False)
    task = load_stored_task(task_root)
    candidate = tmp_path / "candidate.sv"
    candidate.write_text("module toy; endmodule\n")
    plan = build_candidate_validation_plan(
        task,
        candidate,
        work_root=tmp_path / "work",
        preferred_simulator="xrun",
    )

    def fake_run(command, *, cwd, capture_output, text, timeout, check):
        plan.log_path.write_text("xmsim: *E,BOOM\n===========Your Design Passed===========\n")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("rtl_training.oracle.subprocess.run", fake_run)

    result = run_simulation_plan(plan, timeout_s=30)

    assert result.passed is False
