import json
from pathlib import Path
import subprocess

from rtl_training.opencode_runtime import OpenCodeRunRequest, OpenCodeRunResult
from rtl_training.task_store import store_rtllm_tasks
from rtl_training.verifier_benchmark import (
    collect_labeled_candidates,
    read_verifier_verdict,
    run_verifier_batch,
)


ROOT = Path(__file__).resolve().parents[1]


def _create_task_store(tmp_path: Path) -> Path:
    source_root = tmp_path / "RTLLM"
    task_dir = source_root / "Arithmetic" / "Adder" / "adder_8bit"
    task_dir.mkdir(parents=True)
    (task_dir / "design_description.txt").write_text("8-bit adder")
    (task_dir / "verified_adder_8bit.v").write_text("module verified_adder_8bit; endmodule\n")
    (task_dir / "testbench.v").write_text("module testbench; endmodule\n")
    written = store_rtllm_tasks(source_root, tmp_path / "task_store", dataset_name="rtllm_v2_0")
    return written[0].parent


def _write_labeled_candidate(
    *,
    batch_root: Path,
    run_id: str,
    task_id: str,
    oracle_passed: bool,
) -> None:
    task_root = batch_root / run_id / task_id
    (task_root / "submission").mkdir(parents=True, exist_ok=True)
    (task_root / "result").mkdir(parents=True, exist_ok=True)
    (task_root / "submission" / "candidate.sv").write_text("module adder_8bit; endmodule\n")
    record = {
        "dataset_name": "rtllm_v2_0",
        "task_id": task_id,
        "workspace_root": str(task_root),
        "candidate_path": str(task_root / "submission" / "candidate.sv"),
        "opencode_returncode": 0,
        "opencode_stdout_path": str(task_root / "result" / "opencode_stdout.log"),
        "opencode_stderr_path": str(task_root / "result" / "opencode_stderr.log"),
        "oracle_passed": oracle_passed,
        "oracle_log_path": None,
        "error": None,
        "duration_s": 1.0,
    }
    (task_root / "result" / "batch_record.json").write_text(json.dumps(record) + "\n")


def test_collect_labeled_candidates_reads_generator_batch_records(tmp_path: Path) -> None:
    dataset_root = _create_task_store(tmp_path)
    batch_root = tmp_path / "generator_batch"
    _write_labeled_candidate(batch_root=batch_root, run_id="run_01", task_id="adder_8bit", oracle_passed=True)
    _write_labeled_candidate(batch_root=batch_root, run_id="run_02", task_id="adder_8bit", oracle_passed=False)

    examples = collect_labeled_candidates(batch_root, dataset_root)

    assert [example.example_id for example in examples] == ["run_01/adder_8bit", "run_02/adder_8bit"]
    assert [example.oracle_verdict for example in examples] == ["good", "bad"]
    assert all(example.task_root == dataset_root / "adder_8bit" for example in examples)


def test_read_verifier_verdict_normalizes_common_labels(tmp_path: Path) -> None:
    good_result = tmp_path / "good.json"
    good_result.write_text(json.dumps({"verdict": "Passed"}) + "\n")
    bad_result = tmp_path / "bad.json"
    bad_result.write_text(json.dumps({"verdict": "buggy"}) + "\n")

    assert read_verifier_verdict(good_result) == ("good", None)
    assert read_verifier_verdict(bad_result) == ("bad", None)


def test_run_verifier_batch_records_accuracy(tmp_path: Path, monkeypatch) -> None:
    dataset_root = _create_task_store(tmp_path)
    batch_root = tmp_path / "generator_batch"
    _write_labeled_candidate(batch_root=batch_root, run_id="run_01", task_id="adder_8bit", oracle_passed=True)

    def fake_run_opencode(request: OpenCodeRunRequest, *, timeout_s: int = 600) -> OpenCodeRunResult:
        result_path = Path(request.workspace_root) / "result" / "result.json"
        result_path.write_text(
            json.dumps(
                {
                    "status": "completed",
                    "verdict": "good",
                    "confidence": 0.8,
                    "summary": "candidate matches the simple adder spec",
                    "requirements_checked": ["addition"],
                    "evidence_files": [],
                }
            )
            + "\n"
        )
        return OpenCodeRunResult(
            command=("opencode", "run"),
            returncode=0,
            stdout="ok",
            stderr="",
        )

    monkeypatch.setattr("rtl_training.verifier_benchmark.run_opencode", fake_run_opencode)

    summary = run_verifier_batch(
        batch_root,
        dataset_root,
        tmp_path / "verifier_batch",
        template_root=ROOT,
        model="openai/gpt-5-mini",
        opencode_timeout_s=1,
    )

    assert summary.examples_requested == 1
    assert summary.correct_predictions == 1
    assert summary.incorrect_predictions == 0
    assert summary.accuracy == 1.0
    assert summary.candidate_mutations == 0
    assert summary.results[0].predicted_verdict == "good"


def test_run_verifier_batch_disqualifies_candidate_mutation(tmp_path: Path, monkeypatch) -> None:
    dataset_root = _create_task_store(tmp_path)
    batch_root = tmp_path / "generator_batch"
    _write_labeled_candidate(batch_root=batch_root, run_id="run_01", task_id="adder_8bit", oracle_passed=True)

    def fake_run_opencode(request: OpenCodeRunRequest, *, timeout_s: int = 600) -> OpenCodeRunResult:
        candidate_path = Path(request.workspace_root) / "candidate" / "candidate.sv"
        candidate_path.chmod(0o644)
        candidate_path.write_text("module adder_8bit(input a, output y); assign y = a; endmodule\n")
        result_path = Path(request.workspace_root) / "result" / "result.json"
        result_path.write_text(json.dumps({"verdict": "good"}) + "\n")
        return OpenCodeRunResult(
            command=("opencode", "run"),
            returncode=0,
            stdout="ok",
            stderr="",
        )

    monkeypatch.setattr("rtl_training.verifier_benchmark.run_opencode", fake_run_opencode)

    summary = run_verifier_batch(
        batch_root,
        dataset_root,
        tmp_path / "verifier_batch",
        template_root=ROOT,
        model="openai/gpt-5-mini",
        opencode_timeout_s=1,
    )

    assert summary.correct_predictions == 0
    assert summary.incorrect_predictions == 1
    assert summary.candidate_mutations == 1
    assert summary.results[0].candidate_modified is True
    assert "modified candidate RTL" in (summary.results[0].error or "")


def test_run_verifier_batch_records_opencode_timeout_as_error(tmp_path: Path, monkeypatch) -> None:
    dataset_root = _create_task_store(tmp_path)
    batch_root = tmp_path / "generator_batch"
    _write_labeled_candidate(batch_root=batch_root, run_id="run_01", task_id="adder_8bit", oracle_passed=True)

    def fake_run_opencode(request: OpenCodeRunRequest, *, timeout_s: int = 600) -> OpenCodeRunResult:
        raise subprocess.TimeoutExpired(cmd=("opencode", "run"), timeout=timeout_s)

    monkeypatch.setattr("rtl_training.verifier_benchmark.run_opencode", fake_run_opencode)

    summary = run_verifier_batch(
        batch_root,
        dataset_root,
        tmp_path / "verifier_batch",
        template_root=ROOT,
        model="openai/gpt-5-mini",
        opencode_timeout_s=1,
    )

    assert summary.correct_predictions == 0
    assert summary.missing_predictions == 1
    assert summary.results[0].opencode_returncode == -1
    assert "opencode execution error" in (summary.results[0].error or "")
