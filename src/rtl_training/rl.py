from __future__ import annotations

from typing import Any, Sequence


def import_tinker() -> Any:
    try:
        import tinker  # type: ignore
    except ImportError as exc:  # pragma: no cover - only exercised with Tinker installed.
        raise RuntimeError(
            "Install `tinker` and the `tinker-cookbook` repo before running training."
        ) from exc
    return tinker


def group_centered_advantages(rewards: Sequence[float]) -> list[float]:
    if not rewards:
        return []
    mean_reward = sum(rewards) / len(rewards)
    return [reward - mean_reward for reward in rewards]


def build_loss_inputs(
    target_tokens: Sequence[int],
    sampling_logprobs: Sequence[float],
    advantages: Sequence[float],
) -> dict[str, list[float] | list[int]]:
    if len(target_tokens) != len(sampling_logprobs):
        raise ValueError("target_tokens and sampling_logprobs must have the same length")
    if len(target_tokens) != len(advantages):
        raise ValueError("target_tokens and advantages must have the same length")
    return {
        "target_tokens": list(target_tokens),
        "sampling_logprobs": list(sampling_logprobs),
        "advantages": list(advantages),
    }
