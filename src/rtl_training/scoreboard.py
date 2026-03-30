from __future__ import annotations

from dataclasses import asdict, dataclass
import argparse
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DatasetManifestEntry:
    name: str
    role: str
    status: str
    example_count: int | None
    access: str
    default_tier: str | None


@dataclass(frozen=True)
class GeneratorRunSummary:
    dataset_name: str
    summary_path: str
    model: str | None
    tasks_requested: int
    tasks_completed: int
    tasks_passed: int
    tasks_failed: int
    pass_rate: float | None


@dataclass(frozen=True)
class VerifierRunSummary:
    dataset_name: str
    summary_path: str
    model: str | None
    examples_requested: int | None
    examples_completed: int
    correct_predictions: int
    incorrect_predictions: int
    accuracy: float | None
    missing_predictions: int
    candidate_mutations: int


@dataclass(frozen=True)
class DatasetScoreRow:
    name: str
    role: str
    status: str
    access: str
    default_tier: str | None
    configured_examples: int | None
    materialized_tasks: int
    latest_generator: GeneratorRunSummary | None
    latest_verifier: VerifierRunSummary | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "status": self.status,
            "access": self.access,
            "default_tier": self.default_tier,
            "configured_examples": self.configured_examples,
            "materialized_tasks": self.materialized_tasks,
            "latest_generator": (
                None if self.latest_generator is None else asdict(self.latest_generator)
            ),
            "latest_verifier": (
                None if self.latest_verifier is None else asdict(self.latest_verifier)
            ),
        }


@dataclass(frozen=True)
class ScoreboardReport:
    repo_root: str
    dataset_rows: tuple[DatasetScoreRow, ...]
    generator_runs_found: int
    verifier_runs_found: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_root": self.repo_root,
            "generator_runs_found": self.generator_runs_found,
            "verifier_runs_found": self.verifier_runs_found,
            "dataset_rows": [row.to_dict() for row in self.dataset_rows],
        }


def build_scoreboard_report(repo_root: str | Path = ".") -> ScoreboardReport:
    root = Path(repo_root).resolve()
    manifest_entries = _load_dataset_manifest(root)
    materialized_counts = _count_materialized_tasks(root / "data" / "task_store")
    latest_generator, generator_runs_found = _discover_latest_generator_runs(root / "runs")
    latest_verifier, verifier_runs_found = _discover_latest_verifier_runs(root / "runs")

    rows = tuple(
        DatasetScoreRow(
            name=entry.name,
            role=entry.role,
            status=entry.status,
            access=entry.access,
            default_tier=entry.default_tier,
            configured_examples=entry.example_count,
            materialized_tasks=materialized_counts.get(entry.name, 0),
            latest_generator=latest_generator.get(entry.name),
            latest_verifier=latest_verifier.get(entry.name),
        )
        for entry in manifest_entries
    )
    return ScoreboardReport(
        repo_root=str(root),
        dataset_rows=rows,
        generator_runs_found=generator_runs_found,
        verifier_runs_found=verifier_runs_found,
    )


def render_markdown(report: ScoreboardReport) -> str:
    ready_count = sum(1 for row in report.dataset_rows if row.status == "ready")
    materialized_count = sum(1 for row in report.dataset_rows if row.materialized_tasks > 0)

    lines = [
        "# RTL Scoreboard",
        "",
        f"- Repo root: `{report.repo_root}`",
        f"- Datasets in manifest: {len(report.dataset_rows)}",
        f"- Ready datasets: {ready_count}",
        f"- Materialized datasets here: {materialized_count}",
        f"- Generator summaries found under `runs/`: {report.generator_runs_found}",
        f"- Verifier summaries found under `runs/`: {report.verifier_runs_found}",
        "",
        "## Dataset Status",
        "",
        "| Dataset | Manifest | Tier | Configured | Materialized | Latest generator | Latest verifier |",
        "|---|---|---|---:|---:|---|---|",
    ]
    for row in report.dataset_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    _escape_table_cell(row.name),
                    _escape_table_cell(f"{row.status} / {row.role}"),
                    _escape_table_cell(row.default_tier or "--"),
                    _escape_table_cell(_format_count(row.configured_examples)),
                    _escape_table_cell(str(row.materialized_tasks)),
                    _escape_table_cell(_format_generator_summary(row.latest_generator, report.repo_root)),
                    _escape_table_cell(_format_verifier_summary(row.latest_verifier, report.repo_root)),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def _load_dataset_manifest(repo_root: Path) -> tuple[DatasetManifestEntry, ...]:
    manifest_path = repo_root / "configs" / "datasets.json"
    payload = json.loads(manifest_path.read_text())
    rows: list[DatasetManifestEntry] = []
    for raw in payload.get("datasets", ()):
        rows.append(
            DatasetManifestEntry(
                name=str(raw["name"]),
                role=str(raw["role"]),
                status=str(raw["status"]),
                example_count=(
                    None if raw.get("example_count") is None else int(raw["example_count"])
                ),
                access=str(raw.get("access", "unknown")),
                default_tier=(
                    None if raw.get("default_tier") is None else str(raw["default_tier"])
                ),
            )
        )
    return tuple(rows)


def _count_materialized_tasks(task_store_root: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not task_store_root.is_dir():
        return counts
    for dataset_dir in sorted(task_store_root.iterdir()):
        if not dataset_dir.is_dir():
            continue
        count = sum(
            1
            for task_dir in dataset_dir.iterdir()
            if task_dir.is_dir() and (task_dir / "task.json").exists()
        )
        counts[dataset_dir.name] = count
    return counts


def _discover_latest_generator_runs(
    runs_root: Path,
) -> tuple[dict[str, GeneratorRunSummary], int]:
    latest: dict[str, tuple[tuple[int, int, int, int], GeneratorRunSummary]] = {}
    count = 0
    for summary_path in _discover_summary_paths(runs_root):
        payload = _load_json(summary_path)
        if payload is None or not _is_generator_summary(payload):
            continue
        summary = _parse_generator_summary(summary_path, payload)
        if summary is None:
            continue
        count += 1
        rank = _generator_run_rank(summary, summary_path)
        existing = latest.get(summary.dataset_name)
        if existing is None or rank > existing[0]:
            latest[summary.dataset_name] = (rank, summary)
    return {name: item[1] for name, item in latest.items()}, count


def _discover_latest_verifier_runs(
    runs_root: Path,
) -> tuple[dict[str, VerifierRunSummary], int]:
    latest: dict[str, tuple[tuple[int, int, int, int, int], VerifierRunSummary]] = {}
    count = 0
    for summary_path in _discover_summary_paths(runs_root):
        payload = _load_json(summary_path)
        if payload is None or not _is_verifier_summary(payload):
            continue
        summary = _parse_verifier_summary(summary_path, payload)
        if summary is None:
            continue
        count += 1
        rank = _verifier_run_rank(summary, summary_path)
        existing = latest.get(summary.dataset_name)
        if existing is None or rank > existing[0]:
            latest[summary.dataset_name] = (rank, summary)
    return {name: item[1] for name, item in latest.items()}, count


def _discover_summary_paths(runs_root: Path) -> tuple[Path, ...]:
    if not runs_root.is_dir():
        return ()
    return tuple(sorted(runs_root.rglob("summary.json")))


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _is_generator_summary(payload: dict[str, Any]) -> bool:
    return all(
        key in payload
        for key in ("tasks_requested", "tasks_completed", "tasks_passed", "tasks_failed")
    )


def _is_verifier_summary(payload: dict[str, Any]) -> bool:
    return all(
        key in payload
        for key in ("examples_requested", "examples_completed", "accuracy")
    )


def _parse_generator_summary(
    summary_path: Path,
    payload: dict[str, Any],
) -> GeneratorRunSummary | None:
    dataset_name = _dataset_name_from_payload(payload)
    if dataset_name is None:
        return None
    tasks_completed = int(payload["tasks_completed"])
    tasks_passed = int(payload["tasks_passed"])
    pass_rate = None if tasks_completed == 0 else tasks_passed / tasks_completed
    return GeneratorRunSummary(
        dataset_name=dataset_name,
        summary_path=str(summary_path),
        model=None if payload.get("model") is None else str(payload["model"]),
        tasks_requested=int(payload["tasks_requested"]),
        tasks_completed=tasks_completed,
        tasks_passed=tasks_passed,
        tasks_failed=int(payload["tasks_failed"]),
        pass_rate=pass_rate,
    )


def _parse_verifier_summary(
    summary_path: Path,
    payload: dict[str, Any],
) -> VerifierRunSummary | None:
    dataset_name = _dataset_name_from_payload(payload)
    if dataset_name is None:
        return None
    accuracy_raw = payload.get("accuracy")
    return VerifierRunSummary(
        dataset_name=dataset_name,
        summary_path=str(summary_path),
        model=None if payload.get("model") is None else str(payload["model"]),
        examples_requested=(
            None
            if payload.get("examples_requested") is None
            else int(payload["examples_requested"])
        ),
        examples_completed=int(payload["examples_completed"]),
        correct_predictions=int(payload["correct_predictions"]),
        incorrect_predictions=int(payload["incorrect_predictions"]),
        accuracy=None if accuracy_raw is None else float(accuracy_raw),
        missing_predictions=int(payload.get("missing_predictions", 0)),
        candidate_mutations=int(payload.get("candidate_mutations", 0)),
    )


def _dataset_name_from_payload(payload: dict[str, Any]) -> str | None:
    dataset_root = payload.get("dataset_root")
    if isinstance(dataset_root, str) and dataset_root:
        return Path(dataset_root).name
    results = payload.get("results")
    if isinstance(results, list) and results:
        first = results[0]
        if isinstance(first, dict) and first.get("dataset_name") is not None:
            return str(first["dataset_name"])
    return None


def _generator_run_rank(
    summary: GeneratorRunSummary,
    summary_path: Path,
) -> tuple[int, int, int, int]:
    return (
        summary.tasks_completed,
        summary.tasks_requested,
        summary.tasks_passed,
        summary_path.stat().st_mtime_ns,
    )


def _verifier_run_rank(
    summary: VerifierRunSummary,
    summary_path: Path,
) -> tuple[int, int, int, int, int]:
    requested = (
        summary.examples_completed
        if summary.examples_requested is None
        else summary.examples_requested
    )
    return (
        summary.examples_completed,
        requested,
        summary.correct_predictions,
        1 if summary.model is not None else 0,
        summary_path.stat().st_mtime_ns,
    )


def _format_generator_summary(summary: GeneratorRunSummary | None, repo_root: str) -> str:
    if summary is None:
        return "--"
    rate = "--" if summary.pass_rate is None else f"{summary.pass_rate * 100:.1f}%"
    path = _relative_path(summary.summary_path, repo_root)
    model = summary.model or "default"
    return f"{summary.tasks_passed}/{summary.tasks_completed} pass ({rate}) @ {model} [{path}]"


def _format_verifier_summary(summary: VerifierRunSummary | None, repo_root: str) -> str:
    if summary is None:
        return "--"
    accuracy = "--" if summary.accuracy is None else f"{summary.accuracy * 100:.1f}%"
    path = _relative_path(summary.summary_path, repo_root)
    model = summary.model or "default"
    return (
        f"{summary.correct_predictions}/{summary.examples_completed} correct "
        f"({accuracy}) @ {model} [{path}]"
    )


def _format_count(value: int | None) -> str:
    return "--" if value is None else str(value)


def _relative_path(path: str | Path, repo_root: str) -> str:
    absolute = Path(path)
    root = Path(repo_root)
    try:
        return str(absolute.relative_to(root))
    except ValueError:
        return str(absolute)


def _escape_table_cell(value: str) -> str:
    return value.replace("|", "\\|")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m rtl_training.scoreboard")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    report = build_scoreboard_report(args.repo_root)
    if args.format == "json":
        rendered = json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"
    else:
        rendered = render_markdown(report)
    if args.output is not None:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
