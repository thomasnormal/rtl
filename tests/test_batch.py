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


def _create_medium_task_store(tmp_path: Path) -> Path:
    task_root = tmp_path / "task_store" / "opentitan" / "aon_timer"
    (task_root / "public" / "spec").mkdir(parents=True)
    (task_root / "public" / "spec" / "README.md").write_text("aon_timer spec\n")
    (task_root / "public" / "task.json").write_text(
        json.dumps(
            {
                "dataset_name": "opentitan",
                "task_id": "aon_timer",
                "top_module": "aon_timer",
                "deliverables": {
                    "rtl": "submission/",
                    "summary": "result/result.json",
                },
            },
            indent=2,
        )
        + "\n"
    )
    (task_root / "task.json").write_text(
        json.dumps(
            {
                "dataset_name": "opentitan",
                "task_id": "aon_timer",
                "tier": "medium",
                "public": {
                    "directory": "public",
                    "spec": "public/spec/",
                    "task": "public/task.json",
                },
            },
            indent=2,
        )
        + "\n"
    )
    return task_root.parent


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
        (request.workspace_root / "submission" / "candidate.sv").write_text("module adder; endmodule\n")
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
        "submission_dir": str(existing_task_root / "submission"),
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
        (request.workspace_root / "submission" / "candidate.sv").write_text("module adder; endmodule\n")
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
    assert len(opencode_calls) == 1
    assert "adder_8bit" in opencode_calls[0]
    assert (batch_root / "summary.json").exists()


def test_run_generator_batch_stages_episodes_outside_archive_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    dataset_root = _create_dataset(tmp_path)
    staging_root = tmp_path / "ephemeral"
    staged_workspaces: list[Path] = []
    monkeypatch.setenv("RTL_EPISODE_STAGING_ROOT", str(staging_root))

    def fake_run_opencode(request, *, timeout_s):
        staged_workspaces.append(request.workspace_root)
        assert (request.workspace_root / "task" / "spec" / "spec.txt").exists()
        assert (request.workspace_root / "task" / "task.json").exists()
        assert (request.workspace_root / "opencode.json").exists()
        assert (request.workspace_root / ".opencode").is_dir()
        (request.workspace_root / "submission" / "candidate.sv").write_text("module adder; endmodule\n")
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
    )

    assert summary.tasks_completed == 2
    assert staged_workspaces
    assert all(workspace.is_relative_to(staging_root.resolve()) for workspace in staged_workspaces)
    assert all(not workspace.exists() for workspace in staged_workspaces)
    assert (tmp_path / "batch" / "adder_8bit" / "submission" / "candidate.sv").exists()
    assert list(staging_root.iterdir()) == []


def test_run_generator_batch_uses_tier_aware_default_timeouts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    dataset_root = _create_medium_task_store(tmp_path)
    seen: dict[str, int] = {}

    def fake_run_opencode(request, *, timeout_s):
        seen["opencode_timeout_s"] = timeout_s
        (request.workspace_root / "submission" / "candidate.sv").write_text("module aon_timer; endmodule\n")
        (request.workspace_root / "result" / "result.json").write_text('{"status":"completed"}\n')
        return OpenCodeRunResult(
            command=("opencode",),
            returncode=0,
            stdout="ok\n",
            stderr="",
        )

    def fake_validate_generator_episode(episode, *, work_root, preferred_simulator, timeout_s):
        seen["oracle_timeout_s"] = timeout_s
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
        model="openai/gpt-5.4",
        opencode_timeout_s=None,
        oracle_timeout_s=None,
    )

    assert summary.tasks_completed == 1
    assert seen["opencode_timeout_s"] == 2400
    assert seen["oracle_timeout_s"] == 1800
