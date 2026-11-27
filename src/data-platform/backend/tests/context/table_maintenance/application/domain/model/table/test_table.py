"""Test the Table aggregate: registration, management, lifecycle and operation state."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceOperation,
    OverTargetPartition,
    PolicyTarget,
    TableId,
    TableMaintenanceRunId,
    TablePriority,
)
from context.table_maintenance.application.domain.model.table import (
    AppliedPolicyRef,
    AttentionMark,
    InvalidTableTransition,
    OperationState,
    RecordedAttempt,
    Table,
    TableName,
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_discovery_policy import DecidedBy, ManagementDecision
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    DEFAULT_POLICY_ID,
    TableMaintenancePolicyName,
)
from tests.context.table_maintenance.discovery_decision_samples import (
    MANAGED,
    SAMPLE_POLICY_ID,
    UNMANAGED,
)

RUN_1 = "mr-00000000000000000000000001"
DEFAULT_NAME = TableMaintenancePolicyName(value="default")
RUN_2 = "mr-00000000000000000000000002"

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
NAME = TableName(catalog="iceberg", namespace="inventory", table="orders")
DECIDED_BY = DecidedBy(policy_id=SAMPLE_POLICY_ID, policy_version=1, rule_position=1)
OTHER_RULE = DecidedBy(policy_id=SAMPLE_POLICY_ID, policy_version=1, rule_position=2)
NEXT_VERSION = DecidedBy(policy_id=SAMPLE_POLICY_ID, policy_version=2, rule_position=1)
OP = MaintenanceOperation.REWRITE_DATA_FILES


def managed() -> Table:
    """Provide a table registered as managed through a rule."""
    return Table.register(TableId("u1"), NAME, MANAGED, T0)


def test_register_makes_a_managed_table_recording_what_decided_it():
    """A table a managing decision registers is managed and records the policy, version and rule position."""
    t = managed()
    assert t.status == TableStatus.MANAGED
    assert t.is_managed
    assert t.decided_by == DECIDED_BY
    assert t.registered_at == t.updated_at == T0


def test_register_by_an_unmanaging_decision_makes_an_unmanaged_table():
    """A table an unmanaging decision registers is unmanaged and still records what decided it."""
    t = Table.register(TableId("u1"), NAME, UNMANAGED, T0)
    assert t.status == TableStatus.UNMANAGED
    assert not t.is_managed
    assert t.decided_by == UNMANAGED.decided_by
    assert t.registered_at == t.updated_at == T0


def test_register_with_nothing_attached_makes_an_unmanaged_table_decided_by_nothing():
    """A table no discovery policy applies to is registered unmanaged, naming no policy."""
    t = Table.register(TableId("u1"), NAME, ManagementDecision.nothing_attached(), T0)
    assert t.status == TableStatus.UNMANAGED
    assert t.decided_by is None


def test_table_statuses_are_managed_unmanaged_and_dropped():
    """A table is managed, unmanaged or dropped; nothing else."""
    assert [s.value for s in TableStatus] == ["managed", "unmanaged", "dropped"]


def test_unmanage_keeps_the_row_and_records_what_unmanaged_it():
    """Unmanaging keeps the table and its state, and records what unmanaged it."""
    t = managed()
    t.record_operation_result(OP, True, T0, size=ComputeSize.S)
    t.unmanage(UNMANAGED.decided_by, T1)
    assert t.status == TableStatus.UNMANAGED
    assert not t.is_managed
    assert t.decided_by == UNMANAGED.decided_by
    assert t.updated_at == T1
    assert t.operation_state(OP).last_attempt_at == T0


def test_unmanage_with_no_policy_unmanages_a_managed_table():
    """A managed table no policy applies to any more is unmanaged, decided by nothing."""
    t = managed()
    t.unmanage(None, T1)
    assert (t.status, t.decided_by, t.updated_at) == (TableStatus.UNMANAGED, None, T1)


def test_unmanage_an_unmanaged_table_by_the_same_decider_changes_nothing():
    """Unmanaging twice by one decider is idempotent."""
    t = managed()
    t.unmanage(UNMANAGED.decided_by, T1)
    t.unmanage(UNMANAGED.decided_by, T1 + timedelta(hours=1))
    assert t.updated_at == T1


def test_unmanage_an_unmanaged_table_by_another_decider_records_it():
    """An unmanaged table another rule now leaves unmanaged records that rule, and stays unmanaged."""
    t = managed()
    t.unmanage(UNMANAGED.decided_by, T1)
    t.unmanage(OTHER_RULE, T1 + timedelta(hours=1))
    assert (t.status, t.decided_by) == (TableStatus.UNMANAGED, OTHER_RULE)
    assert t.updated_at == T1 + timedelta(hours=1)


def test_manage_an_unmanaged_table_again():
    """Managing an unmanaged table makes it managed under what decides it."""
    t = managed()
    t.unmanage(UNMANAGED.decided_by, T1)
    t.manage(OTHER_RULE, T1 + timedelta(hours=1))
    assert t.status == TableStatus.MANAGED
    assert t.decided_by == OTHER_RULE
    assert t.updated_at == T1 + timedelta(hours=1)


def test_manage_a_managed_table_by_the_same_decider_changes_nothing():
    """Managing a table already managed by an equal decider is idempotent."""
    t = managed()
    t.manage(DecidedBy(policy_id=SAMPLE_POLICY_ID, policy_version=1, rule_position=1), T1)
    assert t.updated_at == T0


def test_manage_a_managed_table_by_another_rule_records_the_rule():
    """A managed table now decided by another including rule records that rule."""
    t = managed()
    t.manage(OTHER_RULE, T1)
    assert t.status == TableStatus.MANAGED
    assert t.decided_by == OTHER_RULE
    assert t.updated_at == T1


def test_manage_a_managed_table_by_a_new_version_records_the_version():
    """The same rule in a new version of the policy is another decider: the table records the version."""
    t = managed()
    t.manage(NEXT_VERSION, T1)
    assert t.decided_by == NEXT_VERSION
    assert t.updated_at == T1


def test_dropped_is_terminal():
    """A dropped table cannot change again."""
    t = managed()
    t.mark_dropped(T1)
    t.mark_dropped(T1)
    assert t.status == TableStatus.DROPPED
    assert not t.is_managed
    commands = [
        lambda: t.manage(DECIDED_BY, T1),
        lambda: t.unmanage(UNMANAGED.decided_by, T1),
        lambda: t.rename(NAME, T1),
        lambda: t.record_operation_result(OP, True, T1, size=ComputeSize.S),
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
    ok = failed.after_success(T1, ComputeSize.S)
    assert ok.consecutive_failures == 0 and ok.last_attempt_at == T1


def test_record_operation_result():
    """A failure raises the failure count and a success resets it, managed or not."""
    t = managed()
    assert t.operation_state(OP) == OperationState()
    t.record_operation_result(OP, False, T1)
    assert t.operation_state(OP).consecutive_failures == 1
    t.unmanage(UNMANAGED.decided_by, T1)
    t.record_operation_result(OP, True, T1, size=ComputeSize.S)
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
    with pytest.raises(InvariantViolation):
        t.updated_at = "2026-01-01T00:00:00Z"  # ty: ignore[invalid-assignment]
    assert t.updated_at == T0


def test_table_name_rejects_an_empty_table_as_a_validation_error():
    """An empty table name is a broken invariant at construction."""
    with pytest.raises(InvariantViolation, match="table name must not be empty"):
        TableName(catalog="iceberg", namespace="inventory", table="")


def test_operation_state_is_immutable():
    """An operation state changes only by building a new one."""
    state = OperationState()
    with pytest.raises(AttributeError, match="is immutable"):
        state.consecutive_failures = 1


def test_table_equality_follows_identity():
    """Two tables with one id are equal even when their state differs."""
    a, b = managed(), managed()
    b.unmanage(UNMANAGED.decided_by, T1)
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
        policy=AppliedPolicyRef(policy_id=DEFAULT_POLICY_ID, version=1, target=None),
        policy_name=DEFAULT_NAME,
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
    mark = AttentionMark(
        since=T1,
        reason="r",
        policy=AppliedPolicyRef(policy_id=DEFAULT_POLICY_ID, version=1, target=None),
        policy_name=DEFAULT_NAME,
    )
    with pytest.raises(InvalidTableTransition):
        t.mark_needs_attention(OP, mark, T1)
    with pytest.raises(InvalidTableTransition):
        t.clear_needs_attention(OP, T1)


def test_recording_the_same_attempt_twice_counts_it_once():
    """A result recorded again for the same attempt of the same run changes nothing."""
    t = managed()
    attempt = RecordedAttempt(run_id=TableMaintenanceRunId(RUN_1), attempt=2)
    t.record_operation_result(OP, False, T0, attempt=attempt)
    t.record_operation_result(OP, False, T1, attempt=attempt)
    state = t.operation_state(OP)
    assert state.consecutive_failures == 1
    assert state.last_attempt_at == T0
    assert t.has_recorded(OP, attempt)


def test_another_attempt_is_recorded():
    """A later attempt, or the same attempt number of another run, is a new result."""
    t = managed()
    t.record_operation_result(OP, False, T0, attempt=RecordedAttempt(run_id=TableMaintenanceRunId(RUN_1), attempt=1))
    t.record_operation_result(OP, False, T0, attempt=RecordedAttempt(run_id=TableMaintenanceRunId(RUN_1), attempt=2))
    t.record_operation_result(OP, False, T0, attempt=RecordedAttempt(run_id=TableMaintenanceRunId(RUN_2), attempt=2))
    assert t.operation_state(OP).consecutive_failures == 3
    assert not t.has_recorded(OP, RecordedAttempt(run_id=TableMaintenanceRunId(RUN_1), attempt=1))
    other_operation = MaintenanceOperation.EXPIRE_SNAPSHOTS
    assert not t.has_recorded(other_operation, RecordedAttempt(run_id=TableMaintenanceRunId(RUN_2), attempt=2))


def test_a_recorded_attempt_holds_a_run_id():
    """The attempt names its run by the run id type, and a malformed id is refused."""
    assert type(RecordedAttempt(run_id=TableMaintenanceRunId(RUN_1), attempt=1).run_id) is TableMaintenanceRunId
    with pytest.raises(InvariantViolation, match="TableMaintenanceRunId must look like mr-"):
        RecordedAttempt(run_id=TableMaintenanceRunId("mr-x"), attempt=1)


@pytest.mark.parametrize(("run_id", "attempt"), [("", 1), (RUN_1, 0)])
def test_a_recorded_attempt_names_a_run_and_a_positive_attempt(run_id, attempt):
    """A recorded attempt needs its run and a positive attempt number."""
    with pytest.raises(InvariantViolation):
        RecordedAttempt(run_id=TableMaintenanceRunId(run_id), attempt=attempt)


@pytest.mark.parametrize(
    "run_id", ["0193f3a2-7c41-7d6e-9a55-1b2c3d4e5f60", "mr-0000000000000000000000000", "rc-00000000000000000000000001"]
)
def test_a_recorded_attempt_refuses_a_run_id_of_another_shape(run_id):
    """A recorded attempt holds an ``mr-`` run id only, like ``TableMaintenanceRunId``; an old UUID is refused."""
    with pytest.raises(InvariantViolation, match="mr-<26 base32 characters>"):
        RecordedAttempt(run_id=TableMaintenanceRunId(run_id), attempt=1)


def test_marks_set_under_another_policy_are_lifted():
    """Only the marks set under a policy other than the one that applies now are lifted."""
    v1 = AppliedPolicyRef(policy_id=DEFAULT_POLICY_ID, version=1, target=None)
    v2 = AppliedPolicyRef(policy_id=DEFAULT_POLICY_ID, version=2, target=None)
    t = managed()
    t.mark_needs_attention(OP, AttentionMark(since=T0, reason="oom", policy=v1, policy_name=DEFAULT_NAME), T0)
    t.mark_needs_attention(
        MaintenanceOperation.EXPIRE_SNAPSHOTS,
        AttentionMark(since=T0, reason="oom", policy=v2, policy_name=DEFAULT_NAME),
        T0,
    )
    assert t.lift_attention_set_under_another_policy(v2, T1) == [OP]
    assert t.operation_state(OP).attention is None
    assert t.operation_state(MaintenanceOperation.EXPIRE_SNAPSHOTS).attention is not None
    assert t.updated_at == T1


def test_lifting_nothing_leaves_the_table_unchanged():
    """With every mark set under the applicable policy, nothing is lifted and the table is untouched."""
    v1 = AppliedPolicyRef(policy_id=DEFAULT_POLICY_ID, version=1, target=None)
    t = managed()
    t.mark_needs_attention(OP, AttentionMark(since=T0, reason="oom", policy=v1, policy_name=DEFAULT_NAME), T0)
    assert t.lift_attention_set_under_another_policy(v1, T1) == []
    assert t.updated_at == T0


def test_a_mark_is_not_lifted_when_its_target_is_read_with_an_empty_uuid():
    """A namespace target read with and without ``"table_uuid": None`` is one target, so its mark is kept."""
    short = PolicyTarget.from_primitives({"type": "namespace", "path": ["iceberg", "e2e"]})
    long = PolicyTarget.from_primitives({"type": "namespace", "path": ["iceberg", "e2e"], "table_uuid": None})
    marked = AppliedPolicyRef(policy_id=DEFAULT_POLICY_ID, version=1, target=short)
    t = managed()
    t.mark_needs_attention(OP, AttentionMark(since=T0, reason="oom", policy=marked, policy_name=DEFAULT_NAME), T0)
    again = AppliedPolicyRef(policy_id=DEFAULT_POLICY_ID, version=1, target=long)
    assert t.lift_attention_set_under_another_policy(again, T1) == []
    assert t.operation_state(OP).attention is not None


def test_a_registered_table_starts_at_p3():
    """A table registered through a rule or without one starts at the default priority P3."""
    assert managed().priority is TablePriority.P3
    assert Table.register(TableId("u1"), NAME, UNMANAGED, T0).priority is TablePriority.P3


def test_set_priority_moves_updated_at():
    """Setting another priority changes it and stamps the change time."""
    t = managed()
    t.set_priority(TablePriority.P1, T1)
    assert t.priority is TablePriority.P1
    assert t.updated_at == T1


def test_set_the_same_priority_is_a_no_op():
    """Setting the priority a table already has leaves its updated time alone."""
    t = managed()
    t.set_priority(TablePriority.P3, T1)
    assert t.priority is TablePriority.P3
    assert t.updated_at == T0


def test_a_dropped_table_refuses_set_priority():
    """A dropped table's priority cannot be changed."""
    t = managed()
    t.mark_dropped(T1)
    with pytest.raises(InvalidTableTransition):
        t.set_priority(TablePriority.P0, T1)


EU = OverTargetPartition(spec_id=0, values=("eu",), since=T0)


def test_recording_over_target_partitions_replaces_them():
    """Recording replaces the partitions the table holds over the target and says it changed."""
    table = managed()
    assert table.record_over_target_partitions((EU,)) is True
    assert table.over_target_partitions == (EU,)


def test_recording_the_same_partitions_changes_nothing():
    """Recording an equal record again is no change."""
    table = managed()
    table.record_over_target_partitions((EU,))
    assert table.record_over_target_partitions((EU,)) is False


def test_recording_does_not_move_updated_at():
    """The over-target record is not a change of maintenance state, so it leaves updated_at."""
    table = managed()
    before = table.updated_at
    table.record_over_target_partitions((EU,))
    assert table.updated_at == before


def test_a_dropped_table_records_nothing():
    """A dropped table keeps its record as it was and reports no change."""
    table = managed()
    table.mark_dropped(T0 + timedelta(days=1))
    assert (table.record_over_target_partitions((EU,)), table.over_target_partitions) == (False, ())


def test_a_success_needs_the_size_it_ran_at():
    """A success is recorded with the size it ran at; one without is refused and changes nothing."""
    t = managed()
    with pytest.raises(ValueError, match="size"):
        t.record_operation_result(OP, True, T0)
    assert t.operation_state(OP) == OperationState()


def test_a_success_that_names_no_fit_does_not_count_towards_a_smaller_size():
    """A success recorded without saying it would have fit a smaller size counts as not fitting one."""
    t = managed()
    for _ in range(OperationState.LOW_USE_RUNS):
        t.record_operation_result(OP, True, T0, size=ComputeSize.M)
    assert t.operation_state(OP).last_successful_size is ComputeSize.M
    assert t.operation_state(OP).low_use_successes == 0
