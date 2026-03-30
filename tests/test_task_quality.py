from __future__ import annotations

import json
from pathlib import Path

import pytest

from rtl_training.task_quality import (
    default_task_quality_rubric_path,
    load_task_quality_rubric,
    score_task_quality,
)


def test_default_task_quality_rubric_loads() -> None:
    rubric = load_task_quality_rubric()

    assert rubric.name == "task_quality_rubric"
    assert rubric.min_score == 0
    assert rubric.max_score == 5
    assert sum(category.weight for category in rubric.categories) == 100
    assert rubric.score_bands[0].name == "excellent"


def test_task_quality_rubric_json_is_well_formed() -> None:
    raw = json.loads(default_task_quality_rubric_path().read_text())

    assert raw["version"] == 1
    assert raw["score_scale"] == {"min": 0, "max": 5}
    assert len(raw["categories"]) >= 5


def test_score_task_quality_returns_weighted_total_and_band() -> None:
    rubric = load_task_quality_rubric()
    scores = {category.id: 5 for category in rubric.categories}

    result = score_task_quality(scores, rubric=rubric)

    assert result.total_score == 100.0
    assert result.band == "excellent"
    assert set(result.weighted_breakdown) == {category.id for category in rubric.categories}


def test_score_task_quality_rejects_missing_categories() -> None:
    rubric = load_task_quality_rubric()
    scores = {rubric.categories[0].id: 5}

    with pytest.raises(ValueError, match="missing rubric scores"):
        score_task_quality(scores, rubric=rubric)


def test_score_task_quality_rejects_out_of_range_values() -> None:
    rubric = load_task_quality_rubric()
    scores = {category.id: 5 for category in rubric.categories}
    scores[rubric.categories[0].id] = 6

    with pytest.raises(ValueError, match="must be between"):
        score_task_quality(scores, rubric=rubric)
