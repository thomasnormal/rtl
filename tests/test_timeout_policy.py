from __future__ import annotations

from pathlib import Path

from rtl_training.task_store import StoredTask
from rtl_training.timeout_policy import (
    recommended_opencode_timeout_s,
    recommended_oracle_timeout_s,
    resolve_opencode_timeout_s,
    resolve_oracle_timeout_s,
)


def _task(tmp_path: Path, *, tier: str | None) -> StoredTask:
    root = tmp_path / "task"
    public_dir = root / "public"
    spec_dir = public_dir / "spec"
    spec_dir.mkdir(parents=True)
    public_task_path = public_dir / "task.json"
    public_task_path.write_text("{}\n")
    return StoredTask(
        root=root,
        dataset_name="dummy",
        task_id="dummy",
        spec_dir=spec_dir,
        public_dir=public_dir,
        public_top_module="dummy",
        public_task_path=public_task_path,
        private_dir=None,
        shared_private_ref=None,
        metadata={},
        oracle=None,
        tier=tier,  # type: ignore[arg-type]
    )


def test_recommended_timeouts_scale_with_tier(tmp_path: Path) -> None:
    small = _task(tmp_path / "small", tier="small")
    medium = _task(tmp_path / "medium", tier="medium")
    large = _task(tmp_path / "large", tier="large")

    assert recommended_opencode_timeout_s(small, agent_name="generator") == 900
    assert recommended_opencode_timeout_s(medium, agent_name="generator") == 2400
    assert recommended_opencode_timeout_s(large, agent_name="generator") == 5400
    assert recommended_opencode_timeout_s(medium, agent_name="verifier") == 1800
    assert recommended_oracle_timeout_s(medium) == 1800


def test_resolve_timeout_prefers_explicit_override(tmp_path: Path) -> None:
    medium = _task(tmp_path / "medium", tier="medium")

    assert resolve_opencode_timeout_s(
        medium,
        agent_name="generator",
        requested_timeout_s=None,
    ) == 2400
    assert resolve_opencode_timeout_s(
        medium,
        agent_name="generator",
        requested_timeout_s=123,
    ) == 123
    assert resolve_oracle_timeout_s(medium, requested_timeout_s=None) == 1800
    assert resolve_oracle_timeout_s(medium, requested_timeout_s=456) == 456
