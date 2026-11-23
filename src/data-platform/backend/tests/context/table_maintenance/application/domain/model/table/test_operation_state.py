"""Test what an operation state remembers: its size and whether it needs attention."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    PolicyTarget,
    PolicyTargetType,
)
from context.table_maintenance.application.domain.model.table import (
    AppliedPolicyRef,
    AttentionMark,
    OperationState,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    TableMaintenancePolicyId,
    TableMaintenancePolicyName,
)

T0 = datetime(2026, 11, 13, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
TARGET = PolicyTarget(type=PolicyTargetType.TABLE, path=("iceberg", "e2e", "orders"), table_uuid="u1")
NIGHTLY = TableMaintenancePolicyId("mp-00000000000000000000000001")
WEEKLY = TableMaintenancePolicyId("mp-00000000000000000000000002")
POLICY = AppliedPolicyRef(policy_id=NIGHTLY, version=1, target=TARGET)
MARK = AttentionMark(
    since=T0,
    reason="out of memory at size L",
    policy=POLICY,
    policy_name=TableMaintenancePolicyName(value="nightly"),
)


def test_start_size_defaults_to_s():
    """An operation that never succeeded starts at S."""
    assert OperationState().start_size() is ComputeSize.S


def test_success_remembers_its_size():
    """A success at a size makes that size the start size."""
    assert OperationState().after_success(T0, ComputeSize.M).start_size() is ComputeSize.M


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
    """The mark holds under the same policy id, version and target, and under no other."""
    state = OperationState().with_attention(MARK)
    assert state.needs_attention_under(AppliedPolicyRef(policy_id=NIGHTLY, version=1, target=TARGET))
    assert not state.needs_attention_under(AppliedPolicyRef(policy_id=NIGHTLY, version=2, target=TARGET))
    assert not state.needs_attention_under(AppliedPolicyRef(policy_id=WEEKLY, version=1, target=TARGET))
    other_target = PolicyTarget(type=PolicyTargetType.NAMESPACE, path=("iceberg", "e2e"))
    assert not state.needs_attention_under(AppliedPolicyRef(policy_id=NIGHTLY, version=1, target=other_target))
    assert not state.needs_attention_under(AppliedPolicyRef(policy_id=NIGHTLY, version=1))
    assert not OperationState().needs_attention_under(POLICY)


def test_a_mark_holds_under_the_same_target_spelled_differently():
    """A namespace target read with and without an empty ``table_uuid`` is one target, so the mark holds."""
    spelled_short = PolicyTarget.from_primitives({"type": "namespace", "path": ["iceberg", "e2e"]})
    spelled_long = PolicyTarget.from_primitives({"type": "namespace", "path": ["iceberg", "e2e"], "table_uuid": None})
    mark = MARK.with_changes(policy=AppliedPolicyRef(policy_id=NIGHTLY, version=1, target=spelled_short))
    state = OperationState().with_attention(mark)
    assert state.needs_attention_under(AppliedPolicyRef(policy_id=NIGHTLY, version=1, target=spelled_long))


def test_a_mark_under_a_table_attachment_holds_after_the_table_is_renamed():
    """The table is its uuid, so the same attachment under the table's new name keeps the mark."""
    renamed = PolicyTarget(type=PolicyTargetType.TABLE, path=("iceberg", "sales", "orders_v2"), table_uuid="u1")
    state = OperationState().with_attention(MARK)
    assert state.needs_attention_under(AppliedPolicyRef(policy_id=NIGHTLY, version=1, target=renamed))
    another_table = TARGET.with_changes(table_uuid="u2")
    assert not state.needs_attention_under(AppliedPolicyRef(policy_id=NIGHTLY, version=1, target=another_table))


def test_a_mark_under_the_platform_default_holds_only_under_it():
    """A mark set under the default policy (no target) holds under the default and not under an attachment."""
    default = AppliedPolicyRef(policy_id=NIGHTLY, version=1)
    state = OperationState().with_attention(MARK.with_changes(policy=default))
    assert state.needs_attention_under(AppliedPolicyRef(policy_id=NIGHTLY, version=1, target=None))
    assert not state.needs_attention_under(POLICY)


def _successes(state: OperationState, size: ComputeSize, *fits: bool) -> OperationState:
    for fit in fits:
        state = state.after_success(T0, size, fits_smaller=fit)
    return state


def test_three_successes_that_fit_the_smaller_size_step_down_one_size():
    """Three successes in a row at the remembered size that would fit the smaller size start the next run there."""
    state = _successes(OperationState().after_success(T0, ComputeSize.M), ComputeSize.M, True, True)
    assert state.start_size() is ComputeSize.M
    stepped = _successes(state, ComputeSize.M, True)
    assert stepped.start_size() is ComputeSize.S
    assert stepped.low_use_successes == 0


def test_a_success_that_would_not_fit_resets_the_streak():
    """A success too large for the smaller size, or unmeasured, starts the count again."""
    state = _successes(OperationState().after_success(T0, ComputeSize.M), ComputeSize.M, True, False, True, True)
    assert state.start_size() is ComputeSize.M
    assert state.low_use_successes == 2


def test_a_success_without_a_verdict_resets_the_streak():
    """A success recorded without saying it fits the smaller size counts as not fitting."""
    state = _successes(OperationState().after_success(T0, ComputeSize.M), ComputeSize.M, True, True)
    state = state.after_success(T0, ComputeSize.M)
    assert state.low_use_successes == 0


def test_a_failure_keeps_the_low_use_streak():
    """A failure is no success at the remembered size; it neither adds to nor resets the count."""
    state = _successes(OperationState().after_success(T0, ComputeSize.M), ComputeSize.M, True, True)
    state = state.after_failure(T1)
    assert _successes(state, ComputeSize.M, True).start_size() is ComputeSize.S


def test_size_s_never_steps_below_s():
    """At S there is no smaller size; the count resets and S stays."""
    state = _successes(OperationState(), ComputeSize.S, True, True, True)
    assert state.start_size() is ComputeSize.S
    assert state.low_use_successes == 0


def test_success_at_a_new_size_starts_a_new_streak():
    """A fitting success at another size than the remembered one counts as the first of a new streak."""
    state = _successes(OperationState().after_success(T0, ComputeSize.M), ComputeSize.M, True, True)
    state = _successes(state, ComputeSize.L, True)
    assert state.start_size() is ComputeSize.L
    assert state.low_use_successes == 1
    assert _successes(state, ComputeSize.L, True, True).start_size() is ComputeSize.M
