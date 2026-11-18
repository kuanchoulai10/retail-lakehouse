"""Test the reconcile planning, submission and job services."""

from __future__ import annotations

import copy
from datetime import timedelta
from typing import Any

import pytest

from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    MaintenanceOperation,
)
from context.table_maintenance.application.domain.model.table import (
    AppliedPolicyRef,
    AttentionMark,
    Table,
    TableId,
    TableName,
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_discovery_rules import (
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    DEFAULT_POLICY_NAME,
    AtLeast,
    MaintenancePolicyContent,
    PartialProgress,
    RewriteDataFilesConditions,
    RewriteDataFilesExecutionPolicy,
    RewriteDataFilesTriggerPolicy,
)
from context.table_maintenance.application.exceptions import ValidationError
from context.table_maintenance.application.port.inbound.table import (
    PlanTableMaintenanceUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    CreateTableMaintenancePolicyUseCaseInput,
    UpdateTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
    AttachTableMaintenancePolicyUseCaseInput,
    DetachTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_reconciliation import (
    RecordTableReconciliationUseCaseInput,
)
from context.table_maintenance.application.port.outbound.table import (
    TableMetadataObservation,
)
from context.table_maintenance.application.service.table_maintenance_policy import (
    CreateTableMaintenancePolicyService,
    UpdateTableMaintenancePolicyService,
)
from context.table_maintenance.application.service.table_maintenance_policy_attachment import (
    AttachTableMaintenancePolicyService,
    DetachTableMaintenancePolicyService,
)
from context.table_maintenance.application.service.table_reconciliation import (
    RecordTableReconciliationService,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policy_attachments_repo import (
    InMemoryTableMaintenancePolicyAttachmentsRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_reconciliations_repo import (
    InMemoryTableReconciliationsRepo,
)
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo
from tests.context.table_maintenance.fakes.plan_service_on_fakes import plan_service_on_fakes
from tests.context.table_maintenance.fakes.policy_with_operation import policy_with_operation
from tests.context.table_maintenance.fakes.recording_send_table_change_gateway import (
    RecordingSendTableChangeGateway,
)
from tests.context.table_maintenance.fakes.track_calls import track_calls

NAME = TableName(catalog="iceberg", namespace="sales", table="orders")
KEY = ("iceberg", "sales", "orders")
OPS = MaintenanceOperation
DEFAULT = MaintenancePolicyContent.platform_default()


def _table(repo, now, uuid="u-1", name=NAME):
    table = Table.register(TableId(uuid), name, TableDiscoveryRuleId("r-1"), now)
    repo.create(table)
    return table


def _partition(spec_id, values, files=10, size=10 * 1024):
    return {
        "spec_id": spec_id,
        "values": values,
        "data_file_count": files,
        "position_delete_file_count": 0,
        "equality_delete_file_count": 0,
        "total_data_file_size_bytes": size,
    }


def _field(name):
    return {
        "field_id": 1000,
        "name": name,
        "source_column": name,
        "source_type": "string",
        "transform": "identity",
    }


def _observe(catalog, now, **overrides):
    fields: dict[str, Any] = {
        "table_uuid": "u-1",
        "current_snapshot_id": 12,
        "specs": [
            {"spec_id": 0, "fields": [_field("region")]},
            {"spec_id": 1, "fields": [_field("country")]},
        ],
        "partitions": [_partition(0, ["eu"]), _partition(1, ["de"])],
        "manifests": [{"length_bytes": 100}] * 5,
        "snapshots": [
            {
                "snapshot_id": i,
                "committed_at": (now - timedelta(days=10, minutes=i)).isoformat(),
            }
            for i in range(1, 13)
        ],
    }
    fields.update(overrides)
    catalog.add_table(*KEY, "u-1")
    catalog.observations[KEY] = TableMetadataObservation(**fields)


@pytest.fixture
def policies(policies_repo):
    """Provide the policies repo holding the platform default policy."""
    return policies_repo


@pytest.fixture
def attachments(attachments_repo):
    """Provide the policy attachments repo."""
    return attachments_repo


@pytest.fixture
def planner(tables_repo, catalog, resolve_applicable_policy):
    """Provide the plan table maintenance service on the fakes."""
    return plan_service_on_fakes(tables_repo, catalog, resolve_applicable_policy)


def _use_policy(policies, now, content):
    """Replace the default policy's content, so it applies to every table."""
    UpdateTableMaintenancePolicyService(
        policies,
        InMemoryTableMaintenancePolicyAttachmentsRepo(),
        InMemoryTablesRepo(),
        RecordingSendTableChangeGateway(),
        clock=lambda: now,
    ).execute(
        UpdateTableMaintenancePolicyUseCaseInput(name=DEFAULT_POLICY_NAME, content=content.to_primitives(), version=1)
    )


def _plan(planner, now, manual=None, uuid="u-1"):
    operations = None if manual is None else tuple(manual)
    return planner.execute(PlanTableMaintenanceUseCaseInput(table_uuid=uuid, now=now, manual_operations=operations))


# --- plan ---


def test_plan_skip_reasons(planner, tables_repo, catalog, now):
    """Each table that cannot be planned is skipped with the reason for it."""
    assert _plan(planner, now, uuid="missing").reason == "dropped"
    dropped = _table(tables_repo, now, uuid="u-d", name=TableName(catalog="c", namespace="n", table="d"))
    dropped.mark_dropped(now)
    unmanaged = _table(tables_repo, now, uuid="u-u", name=TableName(catalog="c", namespace="n", table="u"))
    unmanaged.unmanage(now)
    gone = _table(tables_repo, now)
    results = {uuid: _plan(planner, now, uuid=uuid) for uuid in ("u-d", "u-u", gone.id.value)}
    assert {k: (v.status, v.reason) for k, v in results.items()} == {
        "u-d": ("skip", "dropped"),
        "u-u": ("skip", "unmanaged"),
        "u-1": ("skip", "not_found"),
    }
    assert all(v.operations == () for v in results.values())
    assert results["u-1"].reconcile_interval_seconds == 3600


def test_plan_carries_the_fully_qualified_table_name(planner, tables_repo, catalog, now):
    """The plan carries the fully qualified table name."""
    _table(tables_repo, now)
    _observe(catalog, now)
    assert _plan(planner, now).table_name == "iceberg.sales.orders"


def test_plan_skip_carries_the_table_name_when_the_table_is_known(planner, tables_repo, catalog, now):
    """A skipped plan carries the table name when the table is known and None otherwise."""
    unmanaged = _table(tables_repo, now, uuid="u-u", name=TableName(catalog="c", namespace="n", table="u"))
    unmanaged.unmanage(now)
    assert _plan(planner, now, uuid="u-u").table_name == "c.n.u"
    assert _plan(planner, now, uuid="missing").table_name is None


def test_plan_compaction_has_one_filter_per_spec(planner, tables_repo, catalog, now):
    """A compaction plan has one filter per partition spec."""
    _table(tables_repo, now)
    _observe(catalog, now)
    plan = _plan(planner, now)
    assert (plan.status, plan.reason) == ("planned", None)
    compaction = plan.operations[0]
    assert compaction.operation == "rewrite_data_files"
    assert [f.spec_id for f in compaction.filters] == [0, 1]
    assert "'eu'" in compaction.filters[0].where
    assert "'de'" in compaction.filters[1].where
    assert compaction.procedure_args == {
        "target-file-size-bytes": 536870912,
        "min-input-files": 2,
        "partial-progress.enabled": True,
    }


def test_plan_orders_operations_and_renders_procedure_args(planner, tables_repo, catalog, now):
    """The plan orders its operations and renders the arguments of each procedure."""
    _table(tables_repo, now)
    _observe(catalog, now)
    plan = _plan(planner, now)
    assert [o.operation for o in plan.operations] == [
        "rewrite_data_files",
        "rewrite_manifests",
        "expire_snapshots",
        "remove_orphan_files",
    ]
    by_op = {o.operation: o for o in plan.operations}
    assert by_op["rewrite_manifests"].procedure_args == {}
    assert by_op["rewrite_manifests"].filters == ()
    assert by_op["expire_snapshots"].procedure_args == {
        "older_than": "2026-10-23T12:00:00+00:00",
        "retain_last": 10,
    }
    assert by_op["remove_orphan_files"].procedure_args == {"older_than": "2026-10-21T12:00:00+00:00"}
    assert plan.reconcile_interval_seconds == 3600


def test_plan_target_file_size_comes_from_the_policy(planner, tables_repo, catalog, policies, now):
    """The target file size and reconcile interval in the plan come from the applicable policy."""
    policy = policy_with_operation(
        DEFAULT.with_changes(reconcile_interval=timedelta(minutes=5)),
        OPS.REWRITE_DATA_FILES,
        trigger_policy=RewriteDataFilesTriggerPolicy(
            cooldown=timedelta(hours=1),
            conditions=RewriteDataFilesConditions(reducible_files=AtLeast(at_least=1)),
        ),
        execution_policy=RewriteDataFilesExecutionPolicy(
            target_file_size_bytes=1024, min_input_files=2, partial_progress=PartialProgress(enabled=True)
        ),
    )
    _use_policy(policies, now, policy)
    _table(tables_repo, now)
    _observe(
        catalog,
        now,
        specs=[{"spec_id": 0, "fields": []}],
        partitions=[_partition(0, [], files=20, size=2000)],
    )
    plan = _plan(planner, now)
    assert plan.operations[0].procedure_args["target-file-size-bytes"] == 1024
    assert plan.reconcile_interval_seconds == 300


def test_plan_whole_table_compaction_has_no_filters(planner, tables_repo, catalog, now):
    """A whole table compaction has no filters."""
    _table(tables_repo, now)
    _observe(
        catalog,
        now,
        specs=[{"spec_id": 0, "fields": []}],
        partitions=[_partition(0, [], files=20)],
    )
    compaction = _plan(planner, now).operations[0]
    assert compaction.operation == "rewrite_data_files"
    assert compaction.filters == ()


def test_plan_unsupported_partition_field_falls_back_to_whole_table_compaction(
    planner, tables_repo, catalog, now, caplog
):
    """A partition field that cannot be filtered falls back to whole table compaction and logs it."""
    _table(tables_repo, now)
    binary = {**_field("payload"), "source_type": "binary"}
    _observe(
        catalog,
        now,
        specs=[{"spec_id": 0, "fields": [binary]}],
        partitions=[_partition(0, ["AAE="], files=20)],
    )
    plan = _plan(planner, now)
    assert [o.operation for o in plan.operations] == [
        "rewrite_data_files",
        "rewrite_manifests",
        "expire_snapshots",
        "remove_orphan_files",
    ]
    assert plan.operations[0].filters == ()
    assert "whole table" in caplog.text
    assert "binary" in caplog.text


def test_scheduled_plan_respects_cooldown(planner, tables_repo, catalog, now):
    """A scheduled plan respects the cooldown."""
    table = _table(tables_repo, now)
    for op in OPS.ordered():
        table.record_operation_result(op, True, now - timedelta(minutes=1))
    _observe(catalog, now)
    plan = _plan(planner, now)
    assert (plan.status, plan.operations) == ("planned", ())
    table.operation_states.clear()
    control = _plan(planner, now)
    assert "rewrite_data_files" in [o.operation for o in control.operations]


def test_manual_plan_ignores_disabled_and_cooldown(planner, tables_repo, catalog, policies, now):
    """A manual plan ignores both a disabled operation and the cooldown."""
    _use_policy(policies, now, policy_with_operation(DEFAULT, OPS.REWRITE_DATA_FILES, enabled=False))
    table = _table(tables_repo, now)
    table.record_operation_result(OPS.REMOVE_ORPHAN_FILES, True, now)
    _observe(catalog, now)
    plan = _plan(planner, now, ["remove_orphan_files", "rewrite_data_files"])
    assert plan.status == "planned"
    assert [o.operation for o in plan.operations] == [
        "rewrite_data_files",
        "remove_orphan_files",
    ]
    assert plan.operations[0].filters == ()
    assert plan.operations[1].procedure_args == {"older_than": "2026-10-21T12:00:00+00:00"}


def test_manual_plan_without_a_catalog_observation_is_skipped_not_found(planner, tables_repo, now):
    """A manual plan for a table missing from the catalog is skipped as not found."""
    _table(tables_repo, now)
    plan = _plan(planner, now, ["rewrite_manifests"])
    assert (plan.status, plan.reason, plan.operations) == ("skip", "not_found", ())


@pytest.mark.parametrize("manual", [None, ["rewrite_manifests"]])
def test_plan_skips_when_catalog_table_has_a_different_uuid(planner, tables_repo, catalog, now, manual):
    """A plan is skipped as not found when the catalog table has a different uuid."""
    _table(tables_repo, now)
    _observe(catalog, now, table_uuid="u-recreated")
    plan = _plan(planner, now, manual)
    assert (plan.status, plan.reason, plan.operations) == ("skip", "not_found", ())


def test_manual_plan_rejects_unknown_or_empty_operations(planner, tables_repo, now):
    """A manual plan with unknown or no operations is rejected."""
    _table(tables_repo, now)
    with pytest.raises(ValidationError):
        _plan(planner, now, ["defragment"])
    with pytest.raises(ValidationError):
        _plan(planner, now, [])


def test_plan_reports_malformed_observation_as_validation_error(planner, tables_repo, catalog, now):
    """A malformed observation from the catalog is reported as a ValidationError."""
    _table(tables_repo, now)
    _observe(catalog, now, manifests=[{}])
    with pytest.raises(ValidationError):
        _plan(planner, now)


# --- applicable policy ---


def test_plan_output_names_resolved_policy(planner, tables_repo, catalog, policies, attachments, now):
    """The plan names the policy it applied, its version and where it is attached."""
    _table(tables_repo, now)
    _observe(catalog, now)
    gold = DEFAULT.with_changes(reconcile_interval=timedelta(minutes=10), dry_run=True)
    CreateTableMaintenancePolicyService(policies, clock=lambda: now).execute(
        CreateTableMaintenancePolicyUseCaseInput(name="gold", content=gold.to_primitives())
    )
    AttachTableMaintenancePolicyService(
        policies, attachments, catalog, tables_repo, RecordingSendTableChangeGateway(), clock=lambda: now
    ).execute(
        AttachTableMaintenancePolicyUseCaseInput(target_type="namespace", path=("iceberg", "sales"), policy_name="gold")
    )
    plan = _plan(planner, now)
    assert (plan.policy_name, plan.policy_version) == ("gold", 1)
    assert plan.policy_target == {"type": "namespace", "path": ["iceberg", "sales"]}
    assert (plan.reconcile_interval_seconds, plan.dry_run) == (600, True)


def test_plan_without_attachment_names_the_default_policy(planner, tables_repo, catalog, now):
    """With nothing attached, the plan applies the default policy and has no target."""
    _table(tables_repo, now)
    _observe(catalog, now)
    plan = _plan(planner, now)
    assert (plan.policy_name, plan.policy_version, plan.policy_target) == (DEFAULT_POLICY_NAME, 1, None)


def test_skipped_plan_names_the_policy_for_its_interval(planner, tables_repo, policies, now):
    """A skipped plan of a known table takes its interval from the applicable policy."""
    _use_policy(policies, now, DEFAULT.with_changes(reconcile_interval=timedelta(minutes=2)))
    _table(tables_repo, now).unmanage(now)
    plan = _plan(planner, now)
    assert (plan.reason, plan.reconcile_interval_seconds, plan.policy_name, plan.policy_version) == (
        "unmanaged",
        120,
        DEFAULT_POLICY_NAME,
        2,
    )


# --- checks and dry run ---


def _checks(plan):
    return {c.operation: c for c in plan.checks}


def test_scheduled_plan_reports_a_check_per_operation(planner, tables_repo, catalog, policies, now):
    """A scheduled plan reports one check per operation with its verdict and measurements."""
    _use_policy(policies, now, policy_with_operation(DEFAULT, OPS.REWRITE_MANIFESTS, enabled=False))
    table = _table(tables_repo, now)
    table.record_operation_result(OPS.EXPIRE_SNAPSHOTS, True, now - timedelta(minutes=1))
    _observe(catalog, now)
    plan = _plan(planner, now)
    checks = _checks(plan)
    assert [c.operation for c in plan.checks] == [o.value for o in OPS.ordered()]
    assert checks["rewrite_data_files"].verdict == "due"
    assert checks["rewrite_manifests"].verdict == "off"
    assert checks["expire_snapshots"].verdict == "cooling_down"
    assert checks["expire_snapshots"].next_eligible_at is not None
    assert checks["rewrite_data_files"].next_eligible_at is None
    first = checks["rewrite_data_files"].measurements[0]
    assert (first.key, first.unit, first.comparison, first.met) == ("reducible_files", "count", ">=", True)
    assert isinstance(first.observed, int)
    assert [o.operation for o in plan.operations] == [c.operation for c in plan.checks if c.verdict == "due"]
    assert plan.dry_run is False
    assert plan.table_found is True


def test_dry_run_plans_no_operations_but_reports_due(planner, tables_repo, catalog, policies, now):
    """In dry run a scheduled plan has no operations while its checks still say due."""
    _use_policy(policies, now, DEFAULT.with_changes(dry_run=True))
    _table(tables_repo, now)
    _observe(catalog, now)
    plan = _plan(planner, now)
    assert (plan.status, plan.operations, plan.dry_run) == ("planned", (), True)
    assert _checks(plan)["rewrite_data_files"].verdict == "due"


def test_manual_plan_runs_in_dry_run(planner, tables_repo, catalog, policies, now):
    """A manual plan still returns its operations when the table is in dry run."""
    _use_policy(policies, now, DEFAULT.with_changes(dry_run=True))
    _table(tables_repo, now)
    _observe(catalog, now)
    plan = _plan(planner, now, ["rewrite_manifests"])
    assert [o.operation for o in plan.operations] == ["rewrite_manifests"]
    assert plan.dry_run is True


def test_manual_plan_marks_unrequested_not_checked(planner, tables_repo, catalog, now):
    """A manual plan marks the requested operations due and the rest not checked."""
    _table(tables_repo, now)
    _observe(catalog, now)
    plan = _plan(planner, now, ["rewrite_manifests"])
    verdicts = {c.operation: c.verdict for c in plan.checks}
    assert verdicts == {
        "rewrite_data_files": "not_checked",
        "rewrite_manifests": "due",
        "expire_snapshots": "not_checked",
        "remove_orphan_files": "not_checked",
    }
    assert all(c.measurements == () and c.next_eligible_at is None for c in plan.checks)


def test_missing_table_is_not_found_in_maintenance(planner, now):
    """A table missing from maintenance is skipped as dropped and flagged not found."""
    plan = _plan(planner, now, uuid="missing")
    assert (plan.status, plan.reason, plan.table_found, plan.checks, plan.dry_run) == (
        "skip",
        "dropped",
        False,
        (),
        False,
    )


def test_unmanaged_table_skips_with_table_found(planner, tables_repo, now):
    """An unmanaged table is skipped but the table is found."""
    _table(tables_repo, now).unmanage(now)
    plan = _plan(planner, now)
    assert (plan.status, plan.reason, plan.table_found, plan.checks) == ("skip", "unmanaged", True, ())


def _record(plan, now, **overrides):
    repo = InMemoryTableReconciliationsRepo()
    fields = {
        "reconciliation_id": "rec-1",
        "table_uuid": "u-1",
        "reconciled_at": now,
        "wake_reasons": {"schedule": 1},
        "dry_run": True,
        "status": plan.status,
        "skip_reason": plan.reason,
        "checks": [check.model_dump() for check in plan.checks],
        "run_id": None,
        "run_start_failed": False,
        "policy_name": plan.policy_name,
        "policy_version": plan.policy_version,
        "policy_target": plan.policy_target,
    }
    fields.update(overrides)
    RecordTableReconciliationService(repo).execute(RecordTableReconciliationUseCaseInput(**fields))
    return repo.list_all()[0]


def test_scheduled_plan_checks_can_be_recorded(planner, tables_repo, catalog, policies, now):
    """The checks of a scheduled plan (due, off, cooling down, not needed) are accepted by the record service."""
    _use_policy(policies, now, policy_with_operation(DEFAULT, OPS.REWRITE_MANIFESTS, enabled=False))
    table = _table(tables_repo, now)
    table.record_operation_result(OPS.EXPIRE_SNAPSHOTS, True, now - timedelta(minutes=1))
    _observe(catalog, now)
    plan = _plan(planner, now)
    record = _record(plan, now)
    results = {op.operation.value: op.result.value for op in record.operations}
    assert results["rewrite_manifests"] == "off"
    assert results["expire_snapshots"] == "cooling_down"
    assert results["rewrite_data_files"] == "would_start"


def test_manual_plan_checks_can_be_recorded(planner, tables_repo, catalog, now):
    """The checks of a manual plan (due and not checked) are accepted by the record service."""
    _table(tables_repo, now)
    _observe(catalog, now)
    plan = _plan(planner, now, ["rewrite_data_files"])
    record = _record(plan, now)
    results = {op.operation.value: op.result.value for op in record.operations}
    assert results["rewrite_data_files"] == "would_start"
    assert results["expire_snapshots"] == "not_checked"


# --- needs attention and start size ---


def _mark_under_current_policy(planner, table, tables_repo, now, op=OPS.REWRITE_DATA_FILES):
    """Mark ``op`` as needing attention under the policy that applies now."""
    first = _plan(planner, now)
    applied = AppliedPolicyRef(name=first.policy_name, version=first.policy_version, target=first.policy_target)
    table.mark_needs_attention(op, AttentionMark(since=now, reason="out of memory at size L", policy=applied), now)
    tables_repo.update(table)


def test_plan_reports_needs_attention_in_its_checks(planner, tables_repo, catalog, now):
    """An operation that needs attention under the applicable policy is reported and not planned."""
    table = _table(tables_repo, now)
    _observe(catalog, now)
    _mark_under_current_policy(planner, table, tables_repo, now)
    plan = _plan(planner, now)
    assert _checks(plan)["rewrite_data_files"].verdict == "needs_attention"
    assert "rewrite_data_files" not in [o.operation for o in plan.operations]
    assert "expire_snapshots" in [o.operation for o in plan.operations]


def test_plan_after_a_policy_change_plans_the_marked_operation(planner, tables_repo, catalog, policies, now):
    """Once another policy version applies, the plan lifts the mark for good and plans the operation again."""
    table = _table(tables_repo, now)
    _observe(catalog, now)
    _mark_under_current_policy(planner, table, tables_repo, now)
    _use_policy(policies, now, DEFAULT)
    assert _checks(_plan(planner, now))["rewrite_data_files"].verdict == "due"
    assert tables_repo.get(TableId("u-1")).operation_state(OPS.REWRITE_DATA_FILES).attention is None


def test_a_plan_under_the_marking_policy_saves_nothing(planner, tables_repo, catalog, log, now):
    """A plan that finds every mark under the policy that applies leaves the table as it is."""
    table = _table(tables_repo, now)
    _observe(catalog, now)
    _mark_under_current_policy(planner, table, tables_repo, now)
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    _plan(planner, now)
    assert log == []


def test_lifting_a_mark_keeps_a_change_made_while_the_catalog_was_read(planner, tables_repo, catalog, policies, now):
    """A rename and unmanage that land while the plan reads the catalog survive the save that lifts a mark."""
    table = _table(tables_repo, now)
    _observe(catalog, now)
    _mark_under_current_policy(planner, table, tables_repo, now)
    _use_policy(policies, now, DEFAULT)
    stored_get = tables_repo.get
    tables_repo.get = lambda table_id: copy.deepcopy(stored_get(table_id))
    renamed = TableName(catalog="iceberg", namespace="sales", table="orders_v2")
    observe = catalog.observe_table

    def observe_while_the_table_changes(ref):
        concurrent = tables_repo.get(TableId("u-1"))
        concurrent.rename(renamed, now)
        concurrent.unmanage(now)
        tables_repo.update(concurrent)
        return observe(ref)

    catalog.observe_table = observe_while_the_table_changes
    _plan(planner, now)
    stored = stored_get(TableId("u-1"))
    assert stored.name == renamed
    assert not stored.is_managed
    assert stored.operation_state(OPS.REWRITE_DATA_FILES).attention is None


def test_a_table_dropped_while_the_catalog_was_read_stays_dropped(planner, tables_repo, catalog, policies, now):
    """A drop that lands while the plan reads the catalog is not undone by lifting a mark."""
    table = _table(tables_repo, now)
    _observe(catalog, now)
    _mark_under_current_policy(planner, table, tables_repo, now)
    _use_policy(policies, now, DEFAULT)
    stored_get = tables_repo.get
    tables_repo.get = lambda table_id: copy.deepcopy(stored_get(table_id))
    observe = catalog.observe_table

    def observe_while_the_table_is_dropped(ref):
        concurrent = tables_repo.get(TableId("u-1"))
        concurrent.mark_dropped(now)
        tables_repo.update(concurrent)
        return observe(ref)

    catalog.observe_table = observe_while_the_table_is_dropped
    _plan(planner, now)
    assert stored_get(TableId("u-1")).status == TableStatus.DROPPED


def test_detaching_the_new_policy_does_not_bring_the_block_back(
    planner, tables_repo, catalog, policies, attachments, now
):
    """A mark lifted because another policy applied stays lifted when the earlier policy applies again."""
    table = _table(tables_repo, now)
    _observe(catalog, now)
    _mark_under_current_policy(planner, table, tables_repo, now)
    CreateTableMaintenancePolicyService(policies, clock=lambda: now).execute(
        CreateTableMaintenancePolicyUseCaseInput(name="gold", content=DEFAULT.to_primitives())
    )
    AttachTableMaintenancePolicyService(
        policies, attachments, catalog, tables_repo, RecordingSendTableChangeGateway(), clock=lambda: now
    ).execute(
        AttachTableMaintenancePolicyUseCaseInput(target_type="namespace", path=("iceberg", "sales"), policy_name="gold")
    )
    assert _checks(_plan(planner, now))["rewrite_data_files"].verdict == "due"
    DetachTableMaintenancePolicyService(
        policies, attachments, catalog, tables_repo, RecordingSendTableChangeGateway()
    ).execute(DetachTableMaintenancePolicyUseCaseInput(target_type="namespace", path=("iceberg", "sales")))
    plan = _plan(planner, now)
    assert plan.policy_name == DEFAULT_POLICY_NAME
    assert _checks(plan)["rewrite_data_files"].verdict == "due"


def test_plan_starts_each_operation_at_its_remembered_size(planner, tables_repo, catalog, now):
    """A planned operation starts at the size of its last success, or S."""
    table = _table(tables_repo, now)
    table.record_operation_result(OPS.REWRITE_DATA_FILES, True, now - timedelta(days=30), size=ComputeSize.M)
    _observe(catalog, now)
    sizes = {o.operation: o.start_size for o in _plan(planner, now).operations}
    assert sizes["rewrite_data_files"] == "M"
    assert sizes["expire_snapshots"] == "S"


def test_manual_plan_starts_at_the_remembered_size(planner, tables_repo, catalog, now):
    """A manual plan also starts each operation at its remembered size."""
    table = _table(tables_repo, now)
    table.record_operation_result(OPS.REWRITE_DATA_FILES, True, now, size=ComputeSize.L)
    _observe(catalog, now)
    plan = _plan(planner, now, ["rewrite_data_files"])
    assert [(o.operation, o.start_size) for o in plan.operations] == [("rewrite_data_files", "L")]


def test_reconciliation_records_needs_attention(planner, tables_repo, catalog, now):
    """The needs-attention check of a plan is recorded as needs attention."""
    table = _table(tables_repo, now)
    _observe(catalog, now)
    _mark_under_current_policy(planner, table, tables_repo, now)
    record = _record(_plan(planner, now), now)
    results = {op.operation.value: op.result.value for op in record.operations}
    assert results["rewrite_data_files"] == "needs_attention"
