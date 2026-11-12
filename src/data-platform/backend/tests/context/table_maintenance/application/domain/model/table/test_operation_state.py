"""Test what an operation state remembers: its size and whether it needs attention."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from context.table_maintenance.application.domain.model.shared import ComputeSize
from context.table_maintenance.application.domain.model.table import (
    AppliedPolicyRef,
    AttentionMark,
    OperationState,
)

T0 = datetime(2026, 11, 13, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
TARGET = {"type": "table", "path": ["iceberg", "e2e", "orders"], "table_uuid": "u1"}
POLICY = AppliedPolicyRef(name="nightly", version=1, target=TARGET)
MARK = AttentionMark(since=T0, reason="out of memory at size L", policy=POLICY)


def test_start_size_defaults_to_s():
    """An operation that never succeeded starts at S."""
    assert OperationState().start_size() is ComputeSize.S


def test_success_remembers_its_size():
    """A success at a size makes that size the start size."""
    assert OperationState().after_success(T0, ComputeSize.M).start_size() is ComputeSize.M


def test_success_without_a_size_keeps_the_remembered_one():
    """A success without a known size keeps the remembered size."""
    state = OperationState(last_successful_size=ComputeSize.L)
    assert state.after_success(T0).last_successful_size is ComputeSize.L


def test_failure_keeps_the_remembered_size():
    """A failure changes neither the remembered size nor the start size."""
    state = OperationState(last_successful_size=ComputeSize.M).after_failure(T0)
    assert state.start_size() is ComputeSize.M
    assert state.consecutive_failures == 1


def test_success_clears_attention():
    """A success lifts a needs-attention mark."""
    state = OperationState().with_attention(MARK)
    assert state.attention == MARK
    assert state.after_success(T1, ComputeSize.L).attention is None


def test_failure_keeps_attention():
    """A failure keeps a needs-attention mark."""
    assert OperationState().with_attention(MARK).after_failure(T1).attention == MARK


def test_without_attention_clears_the_mark():
    """Clearing attention removes the mark and keeps the rest."""
    state = OperationState(last_successful_size=ComputeSize.M).with_attention(MARK).without_attention()
    assert state.attention is None
    assert state.last_successful_size is ComputeSize.M


def test_needs_attention_only_under_the_policy_it_was_marked_under():
    """The mark holds under the same policy name, version and target, and under no other."""
    state = OperationState().with_attention(MARK)
    assert state.needs_attention_under(AppliedPolicyRef(name="nightly", version=1, target=dict(TARGET)))
    assert not state.needs_attention_under(AppliedPolicyRef(name="nightly", version=2, target=TARGET))
    assert not state.needs_attention_under(AppliedPolicyRef(name="weekly", version=1, target=TARGET))
    other_target = {"type": "namespace", "path": ["iceberg", "e2e"]}
    assert not state.needs_attention_under(AppliedPolicyRef(name="nightly", version=1, target=other_target))
    assert not OperationState().needs_attention_under(POLICY)


def _successes(state: OperationState, size: ComputeSize, *peaks: int | None) -> OperationState:
    for peak in peaks:
        state = state.after_success(T0, size, peak_heap_percent=peak)
    return state


def test_three_low_use_successes_step_down_one_size():
    """Three successes in a row at the remembered size using under half the heap start the next run one size down."""
    state = _successes(OperationState().after_success(T0, ComputeSize.M), ComputeSize.M, 40, 40)
    assert state.start_size() is ComputeSize.M
    stepped = _successes(state, ComputeSize.M, 40)
    assert stepped.start_size() is ComputeSize.S
    assert stepped.low_use_successes == 0


def test_a_high_use_success_resets_the_low_use_streak():
    """A success using half the heap or more starts the count again."""
    state = _successes(OperationState().after_success(T0, ComputeSize.M), ComputeSize.M, 40, 60, 40, 40)
    assert state.start_size() is ComputeSize.M
    assert state.low_use_successes == 2


def test_exactly_half_the_heap_is_not_low_use():
    """Low use is strictly under the threshold."""
    state = _successes(OperationState().after_success(T0, ComputeSize.M), ComputeSize.M, 50, 50, 50)
    assert state.start_size() is ComputeSize.M
    assert state.low_use_successes == 0


def test_an_unmeasured_success_resets_the_low_use_streak():
    """A success without a measurement says nothing about its use, so the count starts again."""
    state = _successes(OperationState().after_success(T0, ComputeSize.M), ComputeSize.M, 40, 40, None, 40)
    assert state.start_size() is ComputeSize.M
    assert state.low_use_successes == 1


def test_a_failure_keeps_the_low_use_streak():
    """A failure is no success at the remembered size; it neither adds to nor resets the count."""
    state = _successes(OperationState().after_success(T0, ComputeSize.M), ComputeSize.M, 40, 40)
    state = state.after_failure(T1)
    assert _successes(state, ComputeSize.M, 40).start_size() is ComputeSize.S


def test_size_s_never_steps_below_s():
    """At S there is no smaller size; the count resets and S stays."""
    state = _successes(OperationState(), ComputeSize.S, 10, 10, 10)
    assert state.start_size() is ComputeSize.S
    assert state.low_use_successes == 0


def test_success_at_a_new_size_starts_a_new_streak():
    """A low-use success at another size than the remembered one counts as the first of a new streak."""
    state = _successes(OperationState().after_success(T0, ComputeSize.M), ComputeSize.M, 40, 40)
    state = _successes(state, ComputeSize.L, 30)
    assert state.start_size() is ComputeSize.L
    assert state.low_use_successes == 1
    assert _successes(state, ComputeSize.L, 30, 30).start_size() is ComputeSize.M
