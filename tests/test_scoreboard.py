import json
import os
from pathlib import Path

from rtl_training.scoreboard import build_scoreboard_report, render_markdown


def _write_datasets_manifest(repo_root: Path) -> None:
    configs_dir = repo_root / "configs"
    configs_dir.mkdir(parents=True)
    (configs_dir / "datasets.json").write_text(
        json.dumps(
            {
                "datasets": [
                    {
                        "name": "alpha",
                        "role": "anchor_seed",
                        "status": "ready",
                        "example_count": 3,
                        "access": "public",
                        "default_tier": "small",
                    },
                    {
                        "name": "beta",
                        "role": "spec_only_corpus",
                        "status": "planned",
                        "example_count": 2,
                        "access": "public",
                        "default_tier": "large",
                    },
                ]
            },
            indent=2,
        )
        + "\n"
    )


def _write_task_store(repo_root: Path) -> None:
    alpha_root = repo_root / "data" / "task_store" / "alpha"
    (alpha_root / "task_a").mkdir(parents=True)
    (alpha_root / "task_a" / "task.json").write_text("{}\n")
    (alpha_root / "task_b").mkdir(parents=True)
    (alpha_root / "task_b" / "task.json").write_text("{}\n")
    (alpha_root / "scratch_dir").mkdir(parents=True)


def _write_generator_summary(path: Path, *, dataset_name: str, passed: int, completed: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "dataset_root": str(path.parents[3] / "data" / "task_store" / dataset_name),
                "batch_root": str(path.parent),
                "model": "openai/gpt-5-mini",
                "tasks_requested": completed,
                "tasks_completed": completed,
                "tasks_passed": passed,
                "tasks_failed": completed - passed,
                "results": [{"dataset_name": dataset_name}],
            },
            indent=2,
        )
        + "\n"
    )


def _write_verifier_summary(
    path: Path,
    *,
    dataset_name: str,
    correct: int,
    completed: int,
    requested: int | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "dataset_root": str(path.parents[3] / "data" / "task_store" / dataset_name),
                "batch_root": str(path.parent),
                "model": "openai/gpt-5-mini",
                "examples_requested": completed if requested is None else requested,
                "examples_completed": completed,
                "correct_predictions": correct,
                "incorrect_predictions": completed - correct,
                "accuracy": correct / completed,
                "missing_predictions": 0,
                "candidate_mutations": 0,
                "results": [{"dataset_name": dataset_name}],
            },
            indent=2,
        )
        + "\n"
    )


def test_build_scoreboard_report_aggregates_manifest_task_store_and_runs(tmp_path: Path) -> None:
    _write_datasets_manifest(tmp_path)
    _write_task_store(tmp_path)

    older_generator = tmp_path / "runs" / "batches" / "alpha_old" / "summary.json"
    newer_generator = tmp_path / "runs" / "batches" / "alpha_new" / "summary.json"
    verifier_summary = tmp_path / "runs" / "verifier_benchmark" / "alpha_eval" / "summary.json"
    _write_generator_summary(older_generator, dataset_name="alpha", passed=1, completed=2)
    _write_generator_summary(newer_generator, dataset_name="alpha", passed=2, completed=2)
    _write_verifier_summary(verifier_summary, dataset_name="alpha", correct=3, completed=4)

    os.utime(older_generator, (1, 1))
    os.utime(newer_generator, (2, 2))
    os.utime(verifier_summary, (3, 3))

    report = build_scoreboard_report(tmp_path)

    assert report.generator_runs_found == 2
    assert report.verifier_runs_found == 1
    rows = {row.name: row for row in report.dataset_rows}
    assert rows["alpha"].materialized_tasks == 2
    assert rows["alpha"].latest_generator is not None
    assert rows["alpha"].latest_generator.tasks_passed == 2
    assert rows["alpha"].latest_generator.tasks_completed == 2
    assert rows["alpha"].latest_verifier is not None
    assert rows["alpha"].latest_verifier.correct_predictions == 3
    assert rows["alpha"].latest_verifier.examples_completed == 4
    assert rows["beta"].materialized_tasks == 0
    assert rows["beta"].latest_generator is None
    assert rows["beta"].latest_verifier is None


def test_scoreboard_prefers_broader_generator_run_over_newer_narrow_run(tmp_path: Path) -> None:
    _write_datasets_manifest(tmp_path)

    full_generator = tmp_path / "runs" / "batches" / "alpha_full" / "summary.json"
    narrow_generator = tmp_path / "runs" / "batches" / "alpha_smoke" / "summary.json"
    _write_generator_summary(full_generator, dataset_name="alpha", passed=5, completed=6)
    _write_generator_summary(narrow_generator, dataset_name="alpha", passed=1, completed=1)

    os.utime(full_generator, (1, 1))
    os.utime(narrow_generator, (2, 2))

    report = build_scoreboard_report(tmp_path)
    rows = {row.name: row for row in report.dataset_rows}

    assert rows["alpha"].latest_generator is not None
    assert rows["alpha"].latest_generator.tasks_completed == 6
    assert rows["alpha"].latest_generator.tasks_passed == 5


def test_scoreboard_prefers_broader_verifier_run_over_newer_shard(tmp_path: Path) -> None:
    _write_datasets_manifest(tmp_path)

    full_verifier = tmp_path / "runs" / "verifier_benchmark" / "alpha_full" / "summary.json"
    shard_verifier = tmp_path / "runs" / "verifier_benchmark" / "alpha_shard" / "summary.json"
    _write_verifier_summary(full_verifier, dataset_name="alpha", correct=7, completed=9)
    _write_verifier_summary(shard_verifier, dataset_name="alpha", correct=1, completed=1)

    os.utime(full_verifier, (1, 1))
    os.utime(shard_verifier, (2, 2))

    report = build_scoreboard_report(tmp_path)
    rows = {row.name: row for row in report.dataset_rows}

    assert rows["alpha"].latest_verifier is not None
    assert rows["alpha"].latest_verifier.examples_completed == 9
    assert rows["alpha"].latest_verifier.correct_predictions == 7


def test_scoreboard_accepts_merged_verifier_summary_with_null_requested(tmp_path: Path) -> None:
    _write_datasets_manifest(tmp_path)

    merged_verifier = tmp_path / "runs" / "verifier_benchmark" / "alpha_merged" / "summary.json"
    _write_verifier_summary(
        merged_verifier,
        dataset_name="alpha",
        correct=6,
        completed=8,
        requested=None,
    )
    payload = json.loads(merged_verifier.read_text())
    payload["examples_requested"] = None
    payload["model"] = None
    merged_verifier.write_text(json.dumps(payload, indent=2) + "\n")

    report = build_scoreboard_report(tmp_path)
    rows = {row.name: row for row in report.dataset_rows}

    assert rows["alpha"].latest_verifier is not None
    assert rows["alpha"].latest_verifier.examples_requested is None
    assert rows["alpha"].latest_verifier.examples_completed == 8


def test_render_markdown_includes_dataset_and_run_status(tmp_path: Path) -> None:
    _write_datasets_manifest(tmp_path)
    _write_task_store(tmp_path)
    generator_summary = tmp_path / "runs" / "batches" / "alpha" / "summary.json"
    verifier_summary = tmp_path / "runs" / "verifier_benchmark" / "alpha_eval" / "summary.json"
    _write_generator_summary(generator_summary, dataset_name="alpha", passed=1, completed=2)
    _write_verifier_summary(verifier_summary, dataset_name="alpha", correct=3, completed=4)

    report = build_scoreboard_report(tmp_path)
    markdown = render_markdown(report)

    assert "# RTL Scoreboard" in markdown
    assert "| Dataset | Manifest | Tier | Configured | Materialized | Latest generator | Latest verifier |" in markdown
    assert "alpha" in markdown
    assert "1/2 pass (50.0%)" in markdown
    assert "3/4 correct (75.0%)" in markdown
    assert "runs/batches/alpha/summary.json" in markdown
    assert "runs/verifier_benchmark/alpha_eval/summary.json" in markdown
