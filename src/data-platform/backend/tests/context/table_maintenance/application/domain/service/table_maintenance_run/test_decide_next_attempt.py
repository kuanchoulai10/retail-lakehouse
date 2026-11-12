"""Test how the next attempt is decided from a failure's class and the attempt's size."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.shared import ComputeSize
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    FailureClass,
    NextAttempt,
    NextStep,
)
from context.table_maintenance.application.domain.service.table_maintenance_run import (
    decide_next_attempt,
)


def test_oom_at_s_retries_at_m() -> None:
    """An OOM at S retries at M."""
    assert decide_next_attempt(FailureClass.OOM, ComputeSize.S, 1, 3) == NextAttempt(
        step=NextStep.RETRY_LARGER, size=ComputeSize.M
    )


def test_oom_at_m_retries_at_l() -> None:
    """An OOM at M retries at L."""
    assert decide_next_attempt(FailureClass.OOM, ComputeSize.M, 2, 3) == NextAttempt(
        step=NextStep.RETRY_LARGER, size=ComputeSize.L
    )


def test_oom_at_l_needs_attention_even_on_the_last_attempt() -> None:
    """An OOM at the largest size hands the operation to a person, whatever attempts remain."""
    assert decide_next_attempt(FailureClass.OOM, ComputeSize.L, 3, 3) == NextAttempt(step=NextStep.NEEDS_ATTENTION)
    assert decide_next_attempt(FailureClass.OOM, ComputeSize.L, 1, 3) == NextAttempt(step=NextStep.NEEDS_ATTENTION)


def test_oom_at_m_on_the_last_attempt_uses_up_the_attempts() -> None:
    """An OOM below L on the last attempt stops because no attempt is left."""
    assert decide_next_attempt(FailureClass.OOM, ComputeSize.M, 3, 3) == NextAttempt(step=NextStep.ATTEMPTS_USED)


@pytest.mark.parametrize("failure_class", [FailureClass.TIMEOUT, FailureClass.COMMIT_CONFLICT, FailureClass.OTHER])
def test_timeout_conflict_and_other_retry_at_the_same_size(failure_class: FailureClass) -> None:
    """A timeout, a commit conflict or another error retries at the same size."""
    assert decide_next_attempt(failure_class, ComputeSize.M, 1, 3) == NextAttempt(
        step=NextStep.RETRY_SAME, size=ComputeSize.M
    )


def test_last_attempt_of_a_same_size_failure_uses_up_the_attempts() -> None:
    """The last attempt of a same-size failure stops."""
    assert decide_next_attempt(FailureClass.OTHER, ComputeSize.S, 3, 3) == NextAttempt(step=NextStep.ATTEMPTS_USED)


def test_permanent_is_not_retried() -> None:
    """A failure that a retry cannot fix stops at once."""
    assert decide_next_attempt(FailureClass.PERMANENT, ComputeSize.S, 1, 3) == NextAttempt(step=NextStep.NOT_RETRIED)


def test_cancelled_stops() -> None:
    """A cancelled attempt stops."""
    assert decide_next_attempt(FailureClass.CANCELLED, ComputeSize.S, 1, 3) == NextAttempt(step=NextStep.CANCELLED)


@pytest.mark.parametrize("failure_class", list(FailureClass))
def test_still_running_stops_whatever_the_class(failure_class: FailureClass) -> None:
    """An attempt whose job may still be running stops, whatever its class."""
    assert decide_next_attempt(failure_class, ComputeSize.S, 1, 3, still_running=True) == NextAttempt(
        step=NextStep.STILL_RUNNING
    )


def test_attempt_without_a_size_counts_as_s() -> None:
    """An attempt started before sizes existed counts as S."""
    assert decide_next_attempt(FailureClass.OOM, None, 1, 3) == NextAttempt(
        step=NextStep.RETRY_LARGER, size=ComputeSize.M
    )
    assert decide_next_attempt(FailureClass.OTHER, None, 1, 3) == NextAttempt(
        step=NextStep.RETRY_SAME, size=ComputeSize.S
    )


def test_a_retry_carries_a_size_and_a_stop_carries_none() -> None:
    """A next attempt holds a size exactly when it retries."""
    with pytest.raises(ValueError, match="size"):
        NextAttempt(step=NextStep.RETRY_SAME)
    with pytest.raises(ValueError, match="size"):
        NextAttempt(step=NextStep.DONE, size=ComputeSize.S)
