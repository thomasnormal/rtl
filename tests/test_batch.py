import json
from pathlib import Path

from rtl_training.batch import list_task_roots, run_generator_batch
from rtl_training.opencode_runtime import OpenCodeRunResult
from rtl_training.task_store import store_rtllm_tasks


ROOT = Path(__file__).resolve().parents[1]


def _create_dataset(tmp_path: Path) -> Path:
    source_root = tmp_path / "RTLLM"
    for task_id in ("adder_8bit", "adder_16bit"):
        task_dir = source_root / "Arithmetic" / task_id / task_id
        task_dir.mkdir(parents=True)
        (task_dir / "design_description.txt").write_text(f"{task_id} spec\n")
        (task_dir / f"verified_{task_id}.v").write_text(f"module verified_{task_id}; endmodule\n")
        (task_dir / "testbench.v").write_text("module testbench; endmodule\n")
    store_rtllm_tasks(source_root, tmp_path / "task_store", dataset_name="rtllm_v1_1")
    return tmp_path / "task_store" / "rtllm_v1_1"


def test_list_task_roots_returns_sorted_task_dirs(tmp_path: Path) -> None:
    dataset_root = _create_dataset(tmp_path)

    task_roots = list_task_roots(dataset_root)

    assert [task_root.name for task_root in task_roots] == ["adder_16bit", "adder_8bit"]


def test_run_generator_batch_writes_summary_and_records(
    tmp_path: Path,
    monkeypatch,
) -> None:
    dataset_root = _create_dataset(tmp_path)

    def fake_run_opencode(request, *, timeout_s):
        candidate_path = request.workspace_root / "submission" / "candidate.sv"
        candidate_path.write_text("module adder; endmodule\n")
        (request.workspace_root / "result" / "result.json").write_text('{"status":"completed"}\n')
        return OpenCodeRunResult(
            command=("opencode",),
            returncode=0,
            stdout="ok\n",
            stderr="",
        )

    def fake_validate_generator_episode(episode, *, work_root, preferred_simulator, timeout_s):
        log_path = Path(work_root) / episode.task.task_id / "xrun.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("PASS\n")
        return type(
            "FakeOracleResult",
            (),
            {
                "passed": True,
                "plan": type("FakePlan", (), {"log_path": log_path})(),
            },
        )()

    monkeypatch.setattr("rtl_training.batch.run_opencode", fake_run_opencode)
    monkeypatch.setattr("rtl_training.batch.validate_generator_episode", fake_validate_generator_episode)

    summary = run_generator_batch(
        dataset_root,
        tmp_path / "batch",
        template_root=ROOT,
        model="openai/gpt-5-mini",
        output_format="default",
    )

    assert summary.tasks_requested == 2
    assert summary.tasks_completed == 2
    assert summary.tasks_passed == 2
    assert summary.tasks_failed == 0
    assert (tmp_path / "batch" / "summary.json").exists()
    assert (tmp_path / "batch" / "adder_8bit" / "result" / "batch_record.json").exists()


def test_run_generator_batch_can_resume_incomplete_batch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    dataset_root = _create_dataset(tmp_path)
    batch_root = tmp_path / "batch"
    existing_task_root = batch_root / "adder_16bit"
    existing_result_dir = existing_task_root / "result"
    existing_result_dir.mkdir(parents=True)
    existing_record = {
        "dataset_name": "rtllm_v1_1",
        "task_id": "adder_16bit",
        "workspace_root": str(existing_task_root),
        "candidate_path": str(existing_task_root / "submission" / "candidate.sv"),
        "opencode_returncode": 0,
        "opencode_stdout_path": str(existing_result_dir / "opencode_stdout.log"),
        "opencode_stderr_path": str(existing_result_dir / "opencode_stderr.log"),
        "oracle_passed": True,
        "oracle_log_path": str(batch_root / "_oracle_eval" / "adder_16bit" / "xrun.log"),
        "error": None,
        "duration_s": 1.0,
    }
    (existing_result_dir / "batch_record.json").write_text(json.dumps(existing_record) + "\n")

    stale_task_root = batch_root / "adder_8bit"
    stale_task_root.mkdir(parents=True)
    (stale_task_root / "stale.txt").write_text("stale\n")

    opencode_calls: list[str] = []

    def fake_run_opencode(request, *, timeout_s):
        opencode_calls.append(request.workspace_root.name)
        candidate_path = request.workspace_root / "submission" / "candidate.sv"
        candidate_path.write_text("module adder; endmodule\n")
        (request.workspace_root / "result" / "result.json").write_text('{"status":"completed"}\n')
        return OpenCodeRunResult(
            command=("opencode",),
            returncode=0,
            stdout="ok\n",
            stderr="",
        )

    def fake_validate_generator_episode(episode, *, work_root, preferred_simulator, timeout_s):
        log_path = Path(work_root) / episode.task.task_id / "xrun.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("PASS\n")
        return type(
            "FakeOracleResult",
            (),
            {
                "passed": True,
                "plan": type("FakePlan", (), {"log_path": log_path})(),
            },
        )()

    monkeypatch.setattr("rtl_training.batch.run_opencode", fake_run_opencode)
    monkeypatch.setattr("rtl_training.batch.validate_generator_episode", fake_validate_generator_episode)

    summary = run_generator_batch(
        dataset_root,
        batch_root,
        template_root=ROOT,
        model="openai/gpt-5-mini",
        output_format="default",
        resume=True,
    )

    assert summary.tasks_requested == 2
    assert summary.tasks_completed == 2
    assert summary.tasks_passed == 2
    assert summary.tasks_failed == 0
    assert opencode_calls == ["adder_8bit"]
    assert (batch_root / "summary.json").exists()
