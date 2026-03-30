from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class RubricBand:
    name: str
    min_score: int
    description: str


@dataclass(frozen=True)
class RubricCategory:
    id: str
    name: str
    weight: int
    question: str
    evidence: tuple[str, ...]
    anchors: dict[int, str]


@dataclass(frozen=True)
class TaskQualityRubric:
    version: int
    name: str
    min_score: int
    max_score: int
    categories: tuple[RubricCategory, ...]
    score_bands: tuple[RubricBand, ...]
    gating_failures: tuple[str, ...]

    def category_by_id(self, category_id: str) -> RubricCategory:
        for category in self.categories:
            if category.id == category_id:
                return category
        raise KeyError(category_id)


@dataclass(frozen=True)
class TaskQualityResult:
    total_score: float
    band: str
    weighted_breakdown: dict[str, float]


def default_task_quality_rubric_path() -> Path:
    return Path(__file__).resolve().parents[2] / "configs" / "task_quality_rubric.json"


def load_task_quality_rubric(path: str | Path | None = None) -> TaskQualityRubric:
    rubric_path = Path(path) if path is not None else default_task_quality_rubric_path()
    raw = json.loads(rubric_path.read_text())

    min_score = int(raw["score_scale"]["min"])
    max_score = int(raw["score_scale"]["max"])

    categories = tuple(
        RubricCategory(
            id=str(item["id"]),
            name=str(item["name"]),
            weight=int(item["weight"]),
            question=str(item["question"]),
            evidence=tuple(str(x) for x in item.get("evidence", ())),
            anchors={int(k): str(v) for k, v in dict(item["anchors"]).items()},
        )
        for item in raw["categories"]
    )
    score_bands = tuple(
        RubricBand(
            name=str(item["name"]),
            min_score=int(item["min_score"]),
            description=str(item["description"]),
        )
        for item in raw["score_bands"]
    )
    rubric = TaskQualityRubric(
        version=int(raw["version"]),
        name=str(raw["name"]),
        min_score=min_score,
        max_score=max_score,
        categories=categories,
        score_bands=score_bands,
        gating_failures=tuple(str(x) for x in raw.get("gating_failures", ())),
    )
    _validate_rubric(rubric)
    return rubric


def _validate_rubric(rubric: TaskQualityRubric) -> None:
    if rubric.min_score != 0:
        raise ValueError(f"expected rubric min_score=0, got {rubric.min_score}")
    if rubric.max_score <= rubric.min_score:
        raise ValueError("rubric max_score must be greater than min_score")
    total_weight = sum(category.weight for category in rubric.categories)
    if total_weight != 100:
        raise ValueError(f"rubric weights must sum to 100, got {total_weight}")
    ids = [category.id for category in rubric.categories]
    if len(ids) != len(set(ids)):
        raise ValueError("rubric category ids must be unique")
    for category in rubric.categories:
        if not category.anchors:
            raise ValueError(f"rubric category {category.id} must define anchors")
    band_thresholds = [band.min_score for band in rubric.score_bands]
    if band_thresholds != sorted(band_thresholds, reverse=True):
        raise ValueError("score bands must be sorted in descending min_score order")


def score_task_quality(
    raw_scores: dict[str, int | float],
    *,
    rubric: TaskQualityRubric | None = None,
) -> TaskQualityResult:
    rubric = rubric or load_task_quality_rubric()

    expected_ids = {category.id for category in rubric.categories}
    provided_ids = set(raw_scores)
    missing = sorted(expected_ids - provided_ids)
    extra = sorted(provided_ids - expected_ids)
    if missing:
        raise ValueError(f"missing rubric scores: {', '.join(missing)}")
    if extra:
        raise ValueError(f"unknown rubric scores: {', '.join(extra)}")

    weighted_breakdown: dict[str, float] = {}
    total = 0.0
    scale = rubric.max_score - rubric.min_score
    for category in rubric.categories:
        raw_value = float(raw_scores[category.id])
        if raw_value < rubric.min_score or raw_value > rubric.max_score:
            raise ValueError(
                f"score for {category.id} must be between {rubric.min_score} and {rubric.max_score}, "
                f"got {raw_value}"
            )
        weighted = (raw_value / scale) * category.weight * 20.0 / 20.0
        weighted_breakdown[category.id] = weighted
        total += weighted

    band = rubric.score_bands[-1].name
    for candidate in rubric.score_bands:
        if total >= candidate.min_score:
            band = candidate.name
            break
    return TaskQualityResult(
        total_score=round(total, 2),
        band=band,
        weighted_breakdown=weighted_breakdown,
    )
