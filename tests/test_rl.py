from rtl_training.rl import build_loss_inputs, group_centered_advantages


def test_group_centered_advantages_sum_to_zero() -> None:
    advantages = group_centered_advantages([1.0, 4.0, 7.0, 10.0])
    assert round(sum(advantages), 10) == 0.0
    assert advantages[0] < 0.0
    assert advantages[-1] > 0.0


def test_build_loss_inputs_rejects_mismatched_lengths() -> None:
    try:
        build_loss_inputs([1, 2], [-0.2], [0.5, -0.5])
    except ValueError as exc:
        assert "same length" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")
