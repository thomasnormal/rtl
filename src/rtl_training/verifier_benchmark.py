from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time
from typing import Iterable

from .opencode_runtime import run_opencode
from .runtime import DEFAULT_VERIFIER_PROMPT, prepare_verifier_episode


Verdict = str


@dataclass(frozen=True)
class LabeledCandidateExample:
    example_id: str
    source_run_id: str
    dataset_name: str
    task_id: str
    task_root: Path
    candidate_path: Path
    oracle_verdict: Verdict


@dataclass(frozen=True)
class VerifierTaskResult:
    example_id: str
    source_run_id: str
    dataset_name: str
    task_id: str
    task_root: str
    source_candidate_path: str
    workspace_root: str
    opencode_returncode: int
    opencode_stdout_path: str
    opencode_stderr_path: str
    verifier_result_path: str | None
    oracle_verdict: Verdict
    predicted_verdict: Verdict | None
    candidate_modified: bool
    correct: bool
    error: str | None
    duration_s: float


@dataclass(frozen=True)
class VerifierBatchSummary:
    source_batch_root: str
    dataset_root: str
    batch_root: str
    model: str | None
    examples_requested: int
    examples_completed: int
    correct_predictions: int
    incorrect_predictions: int
    accuracy: float
    oracle_good: int
    oracle_bad: int
    predicted_good: int
    predicted_bad: int
    missing_predictions: int
    candidate_mutations: int
    confusion: dict[str, int]
    results: tuple[VerifierTaskResult, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "source_batch_root": self.source_batch_root,
            "dataset_root": self.dataset_root,
            "batch_root": self.batch_root,
            "model": self.model,
            "examples_requested": self.examples_requested,
            "examples_completed": self.examples_completed,
            "correct_predictions": self.correct_predictions,
            "incorrect_predictions": self.incorrect_predictions,
            "accuracy": self.accuracy,
            "oracle_good": self.oracle_good,
            "oracle_bad": self.oracle_bad,
            "predicted_good": self.predicted_good,
            "predicted_bad": self.predicted_bad,
            "missing_predictions": self.missing_predictions,
            "candidate_mutations": self.candidate_mutations,
            "confusion": dict(self.confusion),
            "results": [asdict(result) for result in self.results],
        }


def collect_labeled_candidates(
    source_batch_root: str | Path,
    dataset_root: str | Path,
) -> tuple[LabeledCandidateExample, ...]:
    batch_root = Path(source_batch_root).resolve()
    dataset_root_path = Path(dataset_root).resolve()
    examples: list[LabeledCandidateExample] = []
    for record_path in sorted(batch_root.glob("run_*/**/result/batch_record.json")):
        record = json.loads(record_path.read_text())
        task_id = str(record["task_id"])
        dataset_name = str(record["dataset_name"])
        source_run_id = record_path.parents[2].name
        example_id = f"{source_run_id}/{task_id}"
        candidate_path = record_path.parents[1] / "submission" / "candidate.sv"
        if not candidate_path.exists():
            raise FileNotFoundError(
                f"missing candidate RTL for labeled example {example_id}: {candidate_path}"
            )
        task_root = dataset_root_path / task_id
        if not task_root.exists():
            raise FileNotFoundError(
                f"missing task-store root for labeled example {example_id}: {task_root}"
            )
        examples.append(
            LabeledCandidateExample(
                example_id=example_id,
                source_run_id=source_run_id,
                dataset_name=dataset_name,
                task_id=task_id,
                task_root=task_root,
                candidate_path=candidate_path.resolve(),
                oracle_verdict="good" if bool(record["oracle_passed"]) else "bad",
            )
        )
    return tuple(examples)


def _normalize_verdict(raw_verdict: object) -> Verdict | None:
    if raw_verdict is None:
        return None
    text = str(raw_verdict).strip().lower()
    if text in {"good", "pass", "passed", "correct", "valid", "match", "matched"}:
        return "good"
    if text in {"bad", "fail", "failed", "incorrect", "buggy", "invalid", "mismatch", "mismatched"}:
        return "bad"
    if text.startswith("good") or text.startswith("pass"):
        return "good"
    if text.startswith("bad") or text.startswith("fail"):
        return "bad"
    return None


def read_verifier_verdict(result_path: str | Path) -> tuple[Verdict | None, str | None]:
    path = Path(result_path)
    if not path.exists():
        return None, "verifier did not produce result/result.json"
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return None, f"invalid verifier result JSON: {exc}"

    verdict = _normalize_verdict(payload.get("verdict"))
    if verdict is None:
        return None, "verifier result did not contain a normalized `good`/`bad` verdict"
    return verdict, None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_existing_verifier_results(batch_root: Path) -> dict[str, VerifierTaskResult]:
    results: dict[str, VerifierTaskResult] = {}
    for record_path in sorted(batch_root.glob("run_*/**/result/verifier_batch_record.json")):
        data = json.loads(record_path.read_text())
        record = VerifierTaskResult(**data)
        results[record.example_id] = record
    return results


def run_verifier_batch(
    source_batch_root: str | Path,
    dataset_root: str | Path,
    batch_root: str | Path,
    *,
    template_root: str | Path,
    model: str | None,
    prompt: str = DEFAULT_VERIFIER_PROMPT,
    task_ids: Iterable[str] | None = None,
    run_ids: Iterable[str] | None = None,
    limit: int | None = None,
    opencode_timeout_s: int = 900,
    output_format: str = "default",
    resume: bool = False,
) -> VerifierBatchSummary:
    selected_tasks = set(task_ids or ())
    selected_runs = set(run_ids or ())
    examples = collect_labeled_candidates(source_batch_root, dataset_root)
    if selected_tasks:
        examples = tuple(example for example in examples if example.task_id in selected_tasks)
    if selected_runs:
        examples = tuple(example for example in examples if example.source_run_id in selected_runs)
    if limit is not None:
        examples = examples[:limit]

    batch_root_path = Path(batch_root).resolve()
    batch_root_path.mkdir(parents=True, exist_ok=resume)
    existing_results = _load_existing_verifier_results(batch_root_path) if resume else {}

    results: list[VerifierTaskResult] = []
    for example in examples:
        existing = existing_results.get(example.example_id)
        if existing is not None:
            results.append(existing)
            continue

        workspace_root = batch_root_path / example.source_run_id / example.task_id
        if resume and workspace_root.exists():
            shutil.rmtree(workspace_root)

        result = _run_single_verifier_example(
            example,
            batch_root_path=batch_root_path,
            template_root=template_root,
            model=model,
            prompt=prompt,
            opencode_timeout_s=opencode_timeout_s,
            output_format=output_format,
        )
        results.append(result)

    summary = _summarize_verifier_results(
        source_batch_root=Path(source_batch_root).resolve(),
        dataset_root=Path(dataset_root).resolve(),
        batch_root=batch_root_path,
        model=model,
        results=results,
        examples_requested=len(examples),
    )
    (batch_root_path / "summary.json").write_text(json.dumps(summary.to_dict(), indent=2, sort_keys=True) + "\n")
    return summary


def _run_single_verifier_example(
    example: LabeledCandidateExample,
    *,
    batch_root_path: Path,
    template_root: str | Path,
    model: str | None,
    prompt: str,
    opencode_timeout_s: int,
    output_format: str,
) -> VerifierTaskResult:
    start_time = time.monotonic()
    workspace_root = batch_root_path / example.source_run_id / example.task_id
    episode = prepare_verifier_episode(
        example.task_root,
        example.candidate_path,
        workspace_root,
        template_root=template_root,
        model=model,
        prompt=prompt,
    )
    request = replace(episode.request, output_format=output_format)
    candidate_input_path = episode.workspace.candidate_input_path
    if candidate_input_path is None:
        raise ValueError("verifier workspace did not stage a candidate input path")
    original_candidate_digest = _sha256_file(candidate_input_path)
    opencode_returncode = -1
    opencode_stdout = ""
    opencode_stderr = ""
    opencode_error: str | None = None
    try:
        run_result = run_opencode(request, timeout_s=opencode_timeout_s)
        opencode_returncode = run_result.returncode
        opencode_stdout = run_result.stdout
        opencode_stderr = run_result.stderr
    except Exception as exc:
        opencode_error = f"opencode execution error: {exc}"

    stdout_path = episode.workspace.result_dir / "opencode_stdout.log"
    stderr_path = episode.workspace.result_dir / "opencode_stderr.log"
    stdout_path.write_text(opencode_stdout)
    stderr_path.write_text(opencode_stderr)

    verifier_result_path: str | None = None
    predicted_verdict: Verdict | None = None
    error: str | None = None
    candidate_modified = _sha256_file(candidate_input_path) != original_candidate_digest
    if opencode_error is not None:
        error = opencode_error
    elif opencode_returncode != 0:
        error = f"opencode exited with status {opencode_returncode}"
    else:
        verifier_result_path = str(episode.workspace.result_path)
        predicted_verdict, error = read_verifier_verdict(episode.workspace.result_path)
    if candidate_modified:
        mutation_error = "verifier modified candidate RTL under candidate/"
        error = mutation_error if error is None else f"{error}; {mutation_error}"

    duration_s = time.monotonic() - start_time
    record = VerifierTaskResult(
        example_id=example.example_id,
        source_run_id=example.source_run_id,
        dataset_name=example.dataset_name,
        task_id=example.task_id,
        task_root=str(example.task_root),
        source_candidate_path=str(example.candidate_path),
        workspace_root=str(episode.workspace.root),
        opencode_returncode=opencode_returncode,
        opencode_stdout_path=str(stdout_path),
        opencode_stderr_path=str(stderr_path),
        verifier_result_path=verifier_result_path,
        oracle_verdict=example.oracle_verdict,
        predicted_verdict=predicted_verdict,
        candidate_modified=candidate_modified,
        correct=(predicted_verdict == example.oracle_verdict) and not candidate_modified,
        error=error,
        duration_s=duration_s,
    )
    (episode.workspace.result_dir / "verifier_batch_record.json").write_text(
        json.dumps(asdict(record), indent=2, sort_keys=True) + "\n"
    )
    return record


def _summarize_verifier_results(
    *,
    source_batch_root: Path,
    dataset_root: Path,
    batch_root: Path,
    model: str | None,
    results: list[VerifierTaskResult],
    examples_requested: int,
) -> VerifierBatchSummary:
    oracle_good = sum(1 for result in results if result.oracle_verdict == "good")
    oracle_bad = sum(1 for result in results if result.oracle_verdict == "bad")
    predicted_good = sum(1 for result in results if result.predicted_verdict == "good")
    predicted_bad = sum(1 for result in results if result.predicted_verdict == "bad")
    missing_predictions = sum(1 for result in results if result.predicted_verdict is None)
    candidate_mutations = sum(1 for result in results if result.candidate_modified)
    correct_predictions = sum(1 for result in results if result.correct)
    incorrect_predictions = len(results) - correct_predictions
    accuracy = 0.0 if not results else correct_predictions / len(results)
    confusion = {
        "good_to_good": sum(
            1
            for result in results
            if result.oracle_verdict == "good" and result.predicted_verdict == "good"
        ),
        "good_to_bad": sum(
            1
            for result in results
            if result.oracle_verdict == "good" and result.predicted_verdict == "bad"
        ),
        "bad_to_good": sum(
            1
            for result in results
            if result.oracle_verdict == "bad" and result.predicted_verdict == "good"
        ),
        "bad_to_bad": sum(
            1
            for result in results
            if result.oracle_verdict == "bad" and result.predicted_verdict == "bad"
        ),
    }
    return VerifierBatchSummary(
        source_batch_root=str(source_batch_root),
        dataset_root=str(dataset_root),
        batch_root=str(batch_root),
        model=model,
        examples_requested=examples_requested,
        examples_completed=len(results),
        correct_predictions=correct_predictions,
        incorrect_predictions=incorrect_predictions,
        accuracy=accuracy,
        oracle_good=oracle_good,
        oracle_bad=oracle_bad,
        predicted_good=predicted_good,
        predicted_bad=predicted_bad,
        missing_predictions=missing_predictions,
        candidate_mutations=candidate_mutations,
        confusion=confusion,
        results=tuple(results),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m rtl_training.verifier_benchmark")
    parser.add_argument("source_batch_root")
    parser.add_argument("dataset_root")
    parser.add_argument("batch_root")
    parser.add_argument("--template-root", default=".")
    parser.add_argument("--model", default=None)
    parser.add_argument("--task-id", action="append", dest="task_ids")
    parser.add_argument("--run-id", action="append", dest="run_ids")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--opencode-timeout-s", type=int, default=900)
    parser.add_argument("--output-format", choices=("default", "json"), default="default")
    parser.add_argument("--resume", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    summary = run_verifier_batch(
        args.source_batch_root,
        args.dataset_root,
        args.batch_root,
        template_root=args.template_root,
        model=args.model,
        task_ids=args.task_ids,
        run_ids=args.run_ids,
        limit=args.limit,
        opencode_timeout_s=args.opencode_timeout_s,
        output_format=args.output_format,
        resume=args.resume,
    )
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
