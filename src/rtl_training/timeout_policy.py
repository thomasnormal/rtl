from __future__ import annotations

from .datasets import Tier
from .task_store import StoredTask


_DEFAULT_TASK_TIER: Tier = "small"

_AGENT_TIMEOUTS_S: dict[str, dict[Tier, int]] = {
    "generator": {
        "micro": 600,
        "small": 900,
        "medium": 2400,
        "large": 5400,
        "industrial": 10800,
    },
    "verifier": {
        "micro": 600,
        "small": 900,
        "medium": 1800,
        "large": 3600,
        "industrial": 7200,
    },
}

_ORACLE_TIMEOUTS_S: dict[Tier, int] = {
    "micro": 120,
    "small": 300,
    "medium": 1800,
    "large": 3600,
    "industrial": 7200,
}


def task_tier(task: StoredTask | None) -> Tier:
    if task is None or task.tier is None:
        return _DEFAULT_TASK_TIER
    return task.tier


def recommended_opencode_timeout_s(task: StoredTask | None, *, agent_name: str) -> int:
    try:
        tier_map = _AGENT_TIMEOUTS_S[agent_name]
    except KeyError as exc:
        raise ValueError(f"unknown agent timeout policy for {agent_name!r}") from exc
    return tier_map[task_tier(task)]


def recommended_oracle_timeout_s(task: StoredTask | None) -> int:
    return _ORACLE_TIMEOUTS_S[task_tier(task)]


def resolve_opencode_timeout_s(
    task: StoredTask | None,
    *,
    agent_name: str,
    requested_timeout_s: int | None,
) -> int:
    if requested_timeout_s is not None:
        return int(requested_timeout_s)
    return recommended_opencode_timeout_s(task, agent_name=agent_name)


def resolve_oracle_timeout_s(task: StoredTask | None, *, requested_timeout_s: int | None) -> int:
    if requested_timeout_s is not None:
        return int(requested_timeout_s)
    return recommended_oracle_timeout_s(task)
