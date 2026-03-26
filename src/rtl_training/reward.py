from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Verdict = Literal["good", "bad"]


@dataclass(frozen=True)
class VerifierRewardConfig:
    match_bonus: float = 1.0
    cost_penalty: float = 0.05
    evidence_bonus: float = 0.25
    false_alarm_penalty: float = 0.5

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "VerifierRewardConfig":
        return cls(
            match_bonus=float(raw["match_bonus"]),
            cost_penalty=float(raw["cost_penalty"]),
            evidence_bonus=float(raw["evidence_bonus"]),
            false_alarm_penalty=float(raw["false_alarm_penalty"]),
        )


@dataclass(frozen=True)
class VerifierOutcome:
    oracle_verdict: Verdict
    predicted_verdict: Verdict
    total_cost: float
    evidence_utility: float

    @property
    def matched(self) -> bool:
        return self.oracle_verdict == self.predicted_verdict

    @property
    def false_alarm(self) -> bool:
        return self.oracle_verdict == "good" and self.predicted_verdict == "bad"


def compute_verifier_reward(
    outcome: VerifierOutcome,
    config: VerifierRewardConfig | None = None,
) -> float:
    reward_config = config or VerifierRewardConfig()
    reward = reward_config.match_bonus if outcome.matched else 0.0
    reward -= reward_config.cost_penalty * outcome.total_cost
    reward += reward_config.evidence_bonus * outcome.evidence_utility
    if outcome.false_alarm:
        reward -= reward_config.false_alarm_penalty
    return reward
