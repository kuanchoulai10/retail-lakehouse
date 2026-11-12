"""Test the Table aggregate: registration, management, lifecycle and operation state."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from context.table_maintenance.application.domain.model.shared import ComputeSize, MaintenanceOperation
from context.table_maintenance.application.domain.model.table import (
    AppliedPolicyRef,
    AttentionMark,
    InvalidTableTransition,
    OperationState,
    RecordedAttempt,
    Table,
    TableId,
    TableName,
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_discovery_rules import (
    TableDiscoveryRuleId,
)

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
NAME = TableName(catalog="iceberg", namespace="inventory", table="orders")
RULE = TableDiscoveryRuleId("r1")
OP = MaintenanceOperation.REWRITE_DATA_FILES


def managed() -> Table:
    """Provide a table registered as managed through a rule."""
    return Table.register(TableId("u1"), NAME, RULE, T0)


def test_register_makes_a_managed_table_linked_to_its_rule():
    """A registered table is managed and remembers the rule that manages it."""
    t = managed()
    assert t.status == TableStatus.MANAGED
    assert t.is_managed
    assert t.matched_rule_id == RULE
    assert t.registered_at == t.updated_at == T0


def test_register_unmanaged_makes_an_unmanaged_table_without_a_rule():
    """A table no rule includes is registered as unmanaged, with no managing rule."""
    t = Table.register_unmanaged(TableId("u1"), NAME, T0)
    assert t.status == TableStatus.UNMANAGED
    assert not t.is_managed
    assert t.matched_rule_id is None
    assert t.registered_at == t.updated_at == T0


def test_table_statuses_are_managed_unmanaged_and_dropped():
    """A table is managed, unmanaged or dropped; nothing else."""
    assert [s.value for s in TableStatus] == ["managed", "unmanaged", "dropped"]


def test_unmanage_keeps_the_row_and_forgets_the_rule():
    """Unmanaging keeps the table and its state, and it no longer names a managing rule."""
    t = managed()
    t.record_operation_result(OP, True, T0)
    t.unmanage(T1)
    assert t.status == TableStatus.UNMANAGED
    assert not t.is_managed
    assert t.matched_rule_id is None
    assert t.updated_at == T1
    assert t.operation_state(OP).last_attempt_at == T0


def test_unmanage_an_unmanaged_table_changes_nothing():
    """Unmanaging twice is idempotent."""
    t = managed()
    t.unmanage(T1)
    t.unmanage(T1 + timedelta(hours=1))
    assert t.updated_at == T1


def test_manage_an_unmanaged_table_again():
    """Managing an unmanaged table makes it managed under the deciding rule."""
    t = managed()
    t.unmanage(T1)
    t.manage(TableDiscoveryRuleId("r2"), T1 + timedelta(hours=1))
    assert t.status == TableStatus.MANAGED
    assert t.matched_rule_id == TableDiscoveryRuleId("r2")
    assert t.updated_at == T1 + timedelta(hours=1)


def test_manage_a_managed_table_by_the_same_rule_changes_nothing():
    """Managing a table already managed by that rule is idempotent."""
    t = managed()
    t.manage(RULE, T1)
    assert t.updated_at == T0


def test_manage_a_managed_table_by_another_rule_records_the_rule():
    """A managed table now decided by another include rule records that rule."""
    t = managed()
    t.manage(TableDiscoveryRuleId("r2"), T1)
    assert t.status == TableStatus.MANAGED
    assert t.matched_rule_id == TableDiscoveryRuleId("r2")
    assert t.updated_at == T1


def test_dropped_is_terminal():
    """A dropped table cannot change again."""
    t = managed()
    t.mark_dropped(T1)
    t.mark_dropped(T1)
    assert t.status == TableStatus.DROPPED
    assert not t.is_managed
    commands = [
        lambda: t.manage(RULE, T1),
        lambda: t.unmanage(T1),
        lambda: t.rename(NAME, T1),
        lambda: t.record_operation_result(OP, True, T1),
    ]
    for command in commands:
        with pytest.raises(InvalidTableTransition):
            command()


def test_backoff_doubles_and_caps():
    """The cooldown doubles with each consecutive failure up to a cap."""
    base = timedelta(hours=1)
    for failures, expected in [(0, 1), (1, 2), (3, 8), (10, 24)]:
        s = OperationState(consecutive_failures=failures)
        assert s.effective_cooldown(base) == timedelta(hours=expected)
    assert OperationState(consecutive_failures=2).effective_cooldown(timedelta(hours=30)) == timedelta(hours=30)
    failed = OperationState().after_failure(T0).after_failure(T1)
    assert failed.consecutive_failures == 2 and failed.last_attempt_at == T1
    ok = failed.after_success(T1)
    assert ok.consecutive_failures == 0 and ok.last_attempt_at == T1


def test_record_operation_result():
    """A failure raises the failure count and a success resets it, managed or not."""
    t = managed()
    assert t.operation_state(OP) == OperationState()
    t.record_operation_result(OP, False, T1)
    assert t.operation_state(OP).consecutive_failures == 1
    t.unmanage(T1)
    t.record_operation_result(OP, True, T1)
    assert t.operation_state(OP).consecutive_failures == 0
    assert t.updated_at == T1


def test_rename_keeps_identity():
    """Renaming a table keeps its id and equals the original."""
    t = managed()
    new = TableName(catalog="iceberg", namespace="inventory", table="orders_v2")
    t.rename(new, T1)
    assert t.id == TableId("u1") and t.name == new
    assert t == managed()


def test_table_rejects_wrong_type_on_assignment():
    """Every assignment is validated: a string is not a datetime."""
    t = managed()
    with pytest.raises(ValidationError):
        t.updated_at = "2026-01-01T00:00:00Z"  # ty: ignore[invalid-assignment]
    assert t.updated_at == T0


def test_table_name_rejects_an_empty_table_as_a_validation_error():
    """An empty table name is a broken invariant at construction."""
    with pytest.raises(ValidationError, match="table name must not be empty"):
        TableName(catalog="iceberg", namespace="inventory", table="")


def test_operation_state_is_immutable():
    """An operation state changes only by building a new one."""
    state = OperationState()
    with pytest.raises(ValidationError):
        state.consecutive_failures = 1


def test_table_equality_follows_identity():
    """Two tables with one id are equal even when their state differs."""
    a, b = managed(), managed()
    b.unmanage(T1)
    assert a == b and hash(a) == hash(b)


def test_record_operation_result_remembers_the_size_of_a_success():
    """A success records its size; a later failure keeps it."""
    t = managed()
    t.record_operation_result(OP, True, T1, size=ComputeSize.M)
    t.record_operation_result(OP, False, T1)
    assert t.operation_state(OP).start_size() is ComputeSize.M


def test_mark_and_clear_needs_attention():
    """An operation can be marked as needing attention and cleared again; clearing twice is a no-op."""
    t = managed()
    mark = AttentionMark(
        since=T1,
        reason="out of memory at size L",
        policy=AppliedPolicyRef(name="default", version=1, target=None),
    )
    t.mark_needs_attention(OP, mark, T1)
    assert t.operation_state(OP).attention == mark
    assert t.updated_at == T1
    t.clear_needs_attention(OP, T1 + timedelta(hours=1))
    assert t.operation_state(OP).attention is None
    t.clear_needs_attention(OP, T1 + timedelta(hours=2))
    assert t.updated_at == T1 + timedelta(hours=1)


def test_a_dropped_table_refuses_attention_changes():
    """A dropped table records no operation state change."""
    t = managed()
    t.mark_dropped(T1)
    mark = AttentionMark(since=T1, reason="r", policy=AppliedPolicyRef(name="default", version=1, target=None))
    with pytest.raises(InvalidTableTransition):
        t.mark_needs_attention(OP, mark, T1)
    with pytest.raises(InvalidTableTransition):
        t.clear_needs_attention(OP, T1)


def test_recording_the_same_attempt_twice_counts_it_once():
    """A result recorded again for the same attempt of the same run changes nothing."""
    t = managed()
    attempt = RecordedAttempt(run_id="run-1", attempt=2)
    t.record_operation_result(OP, False, T0, attempt=attempt)
    t.record_operation_result(OP, False, T1, attempt=attempt)
    state = t.operation_state(OP)
    assert state.consecutive_failures == 1
    assert state.last_attempt_at == T0
    assert t.has_recorded(OP, attempt)


def test_another_attempt_is_recorded():
    """A later attempt, or the same attempt number of another run, is a new result."""
    t = managed()
    t.record_operation_result(OP, False, T0, attempt=RecordedAttempt(run_id="run-1", attempt=1))
    t.record_operation_result(OP, False, T0, attempt=RecordedAttempt(run_id="run-1", attempt=2))
    t.record_operation_result(OP, False, T0, attempt=RecordedAttempt(run_id="run-2", attempt=2))
    assert t.operation_state(OP).consecutive_failures == 3
    assert not t.has_recorded(OP, RecordedAttempt(run_id="run-1", attempt=1))
    assert not t.has_recorded(MaintenanceOperation.EXPIRE_SNAPSHOTS, RecordedAttempt(run_id="run-2", attempt=2))


@pytest.mark.parametrize(("run_id", "attempt"), [("", 1), ("run-1", 0)])
def test_a_recorded_attempt_names_a_run_and_a_positive_attempt(run_id, attempt):
    """A recorded attempt needs its run and a positive attempt number."""
    with pytest.raises(ValidationError):
        RecordedAttempt(run_id=run_id, attempt=attempt)


def test_marks_set_under_another_policy_are_lifted():
    """Only the marks set under a policy other than the one that applies now are lifted."""
    v1 = AppliedPolicyRef(name="default", version=1, target=None)
    v2 = AppliedPolicyRef(name="default", version=2, target=None)
    t = managed()
    t.mark_needs_attention(OP, AttentionMark(since=T0, reason="oom", policy=v1), T0)
    t.mark_needs_attention(MaintenanceOperation.EXPIRE_SNAPSHOTS, AttentionMark(since=T0, reason="oom", policy=v2), T0)
    assert t.lift_attention_set_under_another_policy(v2, T1) == [OP]
    assert t.operation_state(OP).attention is None
    assert t.operation_state(MaintenanceOperation.EXPIRE_SNAPSHOTS).attention is not None
    assert t.updated_at == T1


def test_lifting_nothing_leaves_the_table_unchanged():
    """With every mark set under the applicable policy, nothing is lifted and the table is untouched."""
    v1 = AppliedPolicyRef(name="default", version=1, target=None)
    t = managed()
    t.mark_needs_attention(OP, AttentionMark(since=T0, reason="oom", policy=v1), T0)
    assert t.lift_attention_set_under_another_policy(v1, T1) == []
    assert t.updated_at == T0
