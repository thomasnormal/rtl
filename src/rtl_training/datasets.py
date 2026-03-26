from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class DatasetSource:
    name: str
    role: str
    status: str
    example_count: int | None
    has_spec: bool
    has_gold_rtl: bool
    has_testbench: bool
    has_formal_oracle: bool
    fields: tuple[str, ...]
    license: str
    access: str
    notes: str

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "DatasetSource":
        count = raw["example_count"]
        return cls(
            name=str(raw["name"]),
            role=str(raw["role"]),
            status=str(raw["status"]),
            example_count=None if count is None else int(count),
            has_spec=bool(raw["has_spec"]),
            has_gold_rtl=bool(raw["has_gold_rtl"]),
            has_testbench=bool(raw["has_testbench"]),
            has_formal_oracle=bool(raw["has_formal_oracle"]),
            fields=tuple(str(item) for item in raw["fields"]),
            license=str(raw["license"]),
            access=str(raw["access"]),
            notes=str(raw["notes"]),
        )


@dataclass(frozen=True)
class RawTask:
    dataset_name: str
    task_id: str
    source_dir: Path
    source_rel_dir: Path
    spec_path: Path
    gold_rtl_path: Path | None
    testbench_path: Path | None


@dataclass(frozen=True)
class DatasetManifest:
    project: str
    datasets: tuple[DatasetSource, ...]
    recommended_order: tuple[str, ...]

    @classmethod
    def load(cls, path: str | Path) -> "DatasetManifest":
        raw = json.loads(Path(path).read_text())
        return cls(
            project=str(raw["project"]),
            datasets=tuple(DatasetSource.from_dict(item) for item in raw["datasets"]),
            recommended_order=tuple(str(item) for item in raw["recommended_order"]),
        )

    def by_name(self, name: str) -> DatasetSource:
        for source in self.datasets:
            if source.name == name:
                return source
        raise KeyError(name)

    def by_role(self, role: str) -> tuple[DatasetSource, ...]:
        return tuple(source for source in self.datasets if source.role == role)

    def ordered_recommendations(self) -> tuple[DatasetSource, ...]:
        return tuple(self.by_name(name) for name in self.recommended_order)

    def total_example_count(self, role: str | None = None) -> int:
        total = 0
        for source in self.datasets:
            if role is not None and source.role != role:
                continue
            if source.example_count is not None:
                total += source.example_count
        return total

    def validate_dataset_names(self, names: Iterable[str]) -> tuple[str, ...]:
        known = {source.name for source in self.datasets}
        missing = sorted(set(names) - known)
        return tuple(missing)


def _find_first_existing(directory: Path, filenames: tuple[str, ...]) -> Path | None:
    for name in filenames:
        path = directory / name
        if path.exists():
            return path
    return None


def _find_single_verified_rtl(directory: Path) -> Path | None:
    candidates = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix in {".v", ".sv"} and path.name.startswith("verified")
    )
    if not candidates:
        return None
    if len(candidates) > 1:
        names = ", ".join(path.name for path in candidates)
        raise ValueError(f"ambiguous verified RTL files in {directory}: {names}")
    return candidates[0]


def discover_rtllm_tasks(root: str | Path, *, dataset_name: str) -> tuple[RawTask, ...]:
    root_path = Path(root)
    tasks: list[RawTask] = []
    seen_task_ids: set[str] = set()
    for spec_path in sorted(root_path.rglob("design_description.txt")):
        source_dir = spec_path.parent
        testbench_path = _find_first_existing(source_dir, ("testbench.v", "testbench.sv"))
        gold_rtl_path = _find_single_verified_rtl(source_dir)
        if testbench_path is None or gold_rtl_path is None:
            continue
        task_id = source_dir.name
        if task_id in seen_task_ids:
            raise ValueError(f"duplicate RTLLM task id discovered: {task_id}")
        seen_task_ids.add(task_id)
        tasks.append(
            RawTask(
                dataset_name=dataset_name,
                task_id=task_id,
                source_dir=source_dir,
                source_rel_dir=source_dir.relative_to(root_path),
                spec_path=spec_path,
                gold_rtl_path=gold_rtl_path,
                testbench_path=testbench_path,
            )
        )
    return tuple(tasks)


def discover_verilog_eval_tasks(
    root: str | Path,
    *,
    dataset_name: str,
    subset: str = "dataset_spec-to-rtl",
) -> tuple[RawTask, ...]:
    root_path = Path(root)
    subset_path = root_path / subset if (root_path / subset).exists() else root_path

    suffix_map = {
        "_prompt.txt": "spec",
        "_ref.sv": "gold_rtl",
        "_ref.v": "gold_rtl",
        "_test.sv": "testbench",
        "_test.v": "testbench",
    }

    grouped: dict[str, dict[str, Path]] = {}
    for path in sorted(subset_path.iterdir()):
        if not path.is_file():
            continue
        for suffix, field_name in suffix_map.items():
            if path.name.endswith(suffix):
                task_id = path.name[: -len(suffix)]
                grouped.setdefault(task_id, {})[field_name] = path
                break

    missing_fields: list[str] = []
    for task_id, fields in sorted(grouped.items()):
        required = {"spec", "gold_rtl", "testbench"}
        missing = sorted(required - set(fields))
        if missing:
            missing_fields.append(f"{task_id}: {', '.join(missing)}")
    if missing_fields:
        raise ValueError("incomplete VerilogEval tasks: " + "; ".join(missing_fields))

    tasks = []
    for task_id, fields in sorted(grouped.items()):
        tasks.append(
            RawTask(
                dataset_name=dataset_name,
                task_id=task_id,
                source_dir=subset_path,
                source_rel_dir=Path(subset_path.name) / task_id,
                spec_path=fields["spec"],
                gold_rtl_path=fields["gold_rtl"],
                testbench_path=fields["testbench"],
            )
        )
    return tuple(tasks)
