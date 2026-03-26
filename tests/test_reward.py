from rtl_training.reward import (
    VerifierOutcome,
    VerifierRewardConfig,
    compute_verifier_reward,
)


def test_reward_prefers_matched_verdict_with_good_evidence() -> None:
    config = VerifierRewardConfig()
    good = VerifierOutcome(
        oracle_verdict="bad",
        predicted_verdict="bad",
        total_cost=2.0,
        evidence_utility=0.8,
    )
    bad = VerifierOutcome(
        oracle_verdict="bad",
        predicted_verdict="good",
        total_cost=2.0,
        evidence_utility=0.0,
    )
    assert compute_verifier_reward(good, config) > compute_verifier_reward(bad, config)


def test_false_alarm_is_penalized() -> None:
    config = VerifierRewardConfig()
    false_alarm = VerifierOutcome(
        oracle_verdict="good",
        predicted_verdict="bad",
        total_cost=1.0,
        evidence_utility=0.0,
    )
    correct = VerifierOutcome(
        oracle_verdict="good",
        predicted_verdict="good",
        total_cost=1.0,
        evidence_utility=0.0,
    )
    assert compute_verifier_reward(false_alarm, config) < compute_verifier_reward(correct, config)
