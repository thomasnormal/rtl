from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import argparse
import json
from pathlib import Path
import shutil
import time
from typing import Iterable

from .opencode_runtime import OpenCodeRunResult, run_opencode
from .runtime import GeneratorEpisode, prepare_generator_episode, validate_generator_episode


@dataclass(frozen=True)
class BatchTaskResult:
    dataset_name: str
    task_id: str
    workspace_root: str
    candidate_path: str
    opencode_returncode: int
    opencode_stdout_path: str
    opencode_stderr_path: str
    oracle_passed: bool
    oracle_log_path: str | None
    error: str | None
    duration_s: float


@dataclass(frozen=True)
class BatchSummary:
    dataset_root: str
    batch_root: str
    model: str | None
    tasks_requested: int
    tasks_completed: int
    tasks_passed: int
    tasks_failed: int
    results: tuple[BatchTaskResult, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "dataset_root": self.dataset_root,
            "batch_root": self.batch_root,
            "model": self.model,
            "tasks_requested": self.tasks_requested,
            "tasks_completed": self.tasks_completed,
            "tasks_passed": self.tasks_passed,
            "tasks_failed": self.tasks_failed,
            "results": [asdict(result) for result in self.results],
        }


def list_task_roots(dataset_root: str | Path) -> tuple[Path, ...]:
    root = Path(dataset_root).resolve()
    task_roots = []
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / "task.json").exists():
            task_roots.append(child)
    return tuple(task_roots)


def _load_existing_batch_results(batch_root: Path) -> dict[str, BatchTaskResult]:
    results: dict[str, BatchTaskResult] = {}
    for record_path in sorted(batch_root.glob("*/result/batch_record.json")):
        data = json.loads(record_path.read_text())
        record = BatchTaskResult(**data)
        results[record.task_id] = record
    return results


def run_generator_batch(
    dataset_root: str | Path,
    batch_root: str | Path,
    *,
    template_root: str | Path,
    model: str | None,
    task_ids: Iterable[str] | None = None,
    limit: int | None = None,
    opencode_timeout_s: int = 900,
    oracle_timeout_s: int = 60,
    preferred_simulator: str | None = "xrun",
    output_format: str = "default",
    resume: bool = False,
) -> BatchSummary:
    selected = set(task_ids or ())
    task_roots = list_task_roots(dataset_root)
    if selected:
        task_roots = tuple(task_root for task_root in task_roots if task_root.name in selected)
    if limit is not None:
        task_roots = task_roots[:limit]

    batch_root_path = Path(batch_root).resolve()
    batch_root_path.mkdir(parents=True, exist_ok=resume)
    existing_results = _load_existing_batch_results(batch_root_path) if resume else {}

    results: list[BatchTaskResult] = []
    for task_root in task_roots:
        existing = existing_results.get(task_root.name)
        if existing is not None:
            results.append(existing)
            continue

        workspace_root = batch_root_path / task_root.name
        if resume and workspace_root.exists():
            shutil.rmtree(workspace_root)

        result = _run_single_generator_task(
            task_root,
            batch_root_path=batch_root_path,
            template_root=template_root,
            model=model,
            opencode_timeout_s=opencode_timeout_s,
            oracle_timeout_s=oracle_timeout_s,
            preferred_simulator=preferred_simulator,
            output_format=output_format,
        )
        results.append(result)

    summary = BatchSummary(
        dataset_root=str(Path(dataset_root).resolve()),
        batch_root=str(batch_root_path),
        model=model,
        tasks_requested=len(task_roots),
        tasks_completed=len(results),
        tasks_passed=sum(1 for result in results if result.oracle_passed),
        tasks_failed=sum(1 for result in results if not result.oracle_passed),
        results=tuple(results),
    )
    (batch_root_path / "summary.json").write_text(json.dumps(summary.to_dict(), indent=2, sort_keys=True) + "\n")
    return summary


def _run_single_generator_task(
    task_root: Path,
    *,
    batch_root_path: Path,
    template_root: str | Path,
    model: str | None,
    opencode_timeout_s: int,
    oracle_timeout_s: int,
    preferred_simulator: str | None,
    output_format: str,
) -> BatchTaskResult:
    start_time = time.monotonic()
    workspace_root = batch_root_path / task_root.name
    episode = prepare_generator_episode(
        task_root,
        workspace_root,
        template_root=template_root,
        model=model,
    )
    request = replace(episode.request, output_format=output_format)
    run_result = run_opencode(request, timeout_s=opencode_timeout_s)

    stdout_path = episode.workspace.result_dir / "opencode_stdout.log"
    stderr_path = episode.workspace.result_dir / "opencode_stderr.log"
    stdout_path.write_text(run_result.stdout)
    stderr_path.write_text(run_result.stderr)

    oracle_passed = False
    oracle_log_path: str | None = None
    error: str | None = None
    if run_result.returncode != 0:
        error = f"opencode exited with status {run_result.returncode}"
    elif episode.workspace.candidate_output_path is None or not episode.workspace.candidate_output_path.exists():
        error = "generator did not produce submission/candidate.sv"
    else:
        try:
            oracle_result = validate_generator_episode(
                episode,
                work_root=batch_root_path / "_oracle_eval",
                preferred_simulator=preferred_simulator,
                timeout_s=oracle_timeout_s,
            )
            oracle_passed = oracle_result.passed
            oracle_log_path = str(oracle_result.plan.log_path)
            if not oracle_result.passed:
                error = "hidden oracle validation failed"
        except Exception as exc:
            error = f"oracle validation error: {exc}"

    duration_s = time.monotonic() - start_time
    record = BatchTaskResult(
        dataset_name=episode.task.dataset_name,
        task_id=episode.task.task_id,
        workspace_root=str(episode.workspace.root),
        candidate_path=(
            "" if episode.workspace.candidate_output_path is None else str(episode.workspace.candidate_output_path)
        ),
        opencode_returncode=run_result.returncode,
        opencode_stdout_path=str(stdout_path),
        opencode_stderr_path=str(stderr_path),
        oracle_passed=oracle_passed,
        oracle_log_path=oracle_log_path,
        error=error,
        duration_s=duration_s,
    )
    (episode.workspace.result_dir / "batch_record.json").write_text(
        json.dumps(asdict(record), indent=2, sort_keys=True) + "\n"
    )
    return record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m rtl_training.batch")
    parser.add_argument("dataset_root")
    parser.add_argument("batch_root")
    parser.add_argument("--template-root", default=".")
    parser.add_argument("--model", default=None)
    parser.add_argument("--task-id", action="append", dest="task_ids")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--opencode-timeout-s", type=int, default=900)
    parser.add_argument("--oracle-timeout-s", type=int, default=60)
    parser.add_argument("--preferred-simulator", default="xrun")
    parser.add_argument("--output-format", choices=("default", "json"), default="default")
    parser.add_argument("--resume", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    summary = run_generator_batch(
        args.dataset_root,
        args.batch_root,
        template_root=args.template_root,
        model=args.model,
        task_ids=args.task_ids,
        limit=args.limit,
        opencode_timeout_s=args.opencode_timeout_s,
        oracle_timeout_s=args.oracle_timeout_s,
        preferred_simulator=args.preferred_simulator,
        output_format=args.output_format,
        resume=args.resume,
    )
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
