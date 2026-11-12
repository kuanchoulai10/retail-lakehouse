"""Test the GetTableHealthService."""

from __future__ import annotations

from typing import Any

import pytest

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
)
from context.table_maintenance.application.domain.model.table import (
    AppliedPolicyRef,
    AttentionMark,
    Table,
    TableId,
    TableName,
)
from context.table_maintenance.application.domain.model.table_discovery_rules import (
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    DEFAULT_POLICY_NAME,
    MaintenancePolicyContent,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table import (
    GetTableHealthUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    UpdateTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
    ResolveApplicableTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.outbound.table import (
    TableMetadataObservation,
)
from context.table_maintenance.application.service.table import GetTableHealthService
from context.table_maintenance.application.service.table_maintenance_policy import (
    UpdateTableMaintenancePolicyService,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policy_attachments_repo import (
    InMemoryTableMaintenancePolicyAttachmentsRepo,
)
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo
from tests.context.table_maintenance.fakes.policy_with_operation import policy_with_operation
from tests.context.table_maintenance.fakes.recording_send_table_change_gateway import (
    RecordingSendTableChangeGateway,
)

KEY = ("iceberg", "sales", "orders")
NAME = TableName(catalog=KEY[0], namespace=KEY[1], table=KEY[2])


def _register(repo, now):
    table = Table.register(TableId("u-1"), NAME, TableDiscoveryRuleId("r-1"), now)
    repo.create(table)
    return table


def _partition(values, pos=0, eq=0):
    return {
        "spec_id": 0,
        "values": values,
        "data_file_count": 10,
        "position_delete_file_count": pos,
        "equality_delete_file_count": eq,
        "total_data_file_size_bytes": 10 * 1024,
    }


def _observe(catalog, **overrides):
    fields: dict[str, Any] = {
        "table_uuid": "u-1",
        "current_snapshot_id": 12,
        "specs": [],
        "partitions": [_partition(["eu"])],
        "manifests": [],
        "snapshots": [],
    }
    fields.update(overrides)
    catalog.add_table(*KEY, "u-1")
    catalog.observations[KEY] = TableMetadataObservation(**fields)


@pytest.fixture
def service(tables_repo, catalog, resolve_applicable_policy, clock):
    """Provide the table health service on the fakes."""
    return GetTableHealthService(tables_repo, catalog, resolve_applicable_policy, clock=clock)


def _health(service):
    return service.execute(GetTableHealthUseCaseInput(uuid="u-1"))


def test_managed_table_reports_each_operation_in_order(service, tables_repo, catalog, now):
    """A managed table is scheduled and reports every operation in canonical order."""
    _register(tables_repo, now)
    _observe(catalog)

    output = _health(service)

    assert output.scheduled is True
    assert output.not_scheduled_reason is None
    assert [item.operation for item in output.operations] == [
        "rewrite_data_files",
        "rewrite_manifests",
        "expire_snapshots",
        "remove_orphan_files",
    ]
    compaction = output.operations[0]
    assert compaction.verdict == "due"
    assert compaction.measured is not None
    assert compaction.size_source == "default"


def test_health_assesses_with_the_applicable_policy(service, tables_repo, catalog, policies_repo, now):
    """The operations are assessed against the policy that applies to the table, not its settings."""
    content = policy_with_operation(
        MaintenancePolicyContent.platform_default(), MaintenanceOperation.REWRITE_DATA_FILES, enabled=False
    )
    UpdateTableMaintenancePolicyService(
        policies_repo,
        InMemoryTableMaintenancePolicyAttachmentsRepo(),
        InMemoryTablesRepo(),
        RecordingSendTableChangeGateway(),
        clock=lambda: now,
    ).execute(
        UpdateTableMaintenancePolicyUseCaseInput(name=DEFAULT_POLICY_NAME, content=content.to_primitives(), version=1)
    )
    _register(tables_repo, now)
    _observe(catalog)

    output = _health(service)

    assert output.operations[0].verdict == "disabled"


def test_unmanaged_table_is_not_scheduled_but_assessed(service, tables_repo, catalog, now):
    """An unmanaged table is reported as not scheduled but its operations are still assessed."""
    _register(tables_repo, now).unmanage(now)
    _observe(catalog)

    output = _health(service)

    assert output.scheduled is False
    assert output.not_scheduled_reason == "unmanaged"
    assert len(output.operations) == 4


def test_every_managed_table_is_scheduled_and_assessed(service, tables_repo, catalog, now):
    """A managed table needs nothing of its own to be scheduled: the applicable policy always applies."""
    _register(tables_repo, now)
    _observe(catalog)

    output = _health(service)

    assert (output.scheduled, output.not_scheduled_reason) == (True, None)
    assert len(output.operations) == 4


def test_delete_file_counts_are_summed(service, tables_repo, catalog, now):
    """Position and equality delete files are summed across partitions."""
    _register(tables_repo, now)
    _observe(
        catalog,
        partitions=[_partition(["eu"], pos=2, eq=1), _partition(["us"], pos=3, eq=4)],
    )

    output = _health(service)

    assert output.position_delete_files == 5
    assert output.equality_delete_files == 5


def test_health_404_when_not_in_catalog(service, tables_repo, now):
    """A table missing from the catalog raises NotFoundError."""
    _register(tables_repo, now)

    with pytest.raises(NotFoundError, match="is not in the catalog$"):
        _health(service)


def test_health_shows_needs_attention(service, tables_repo, catalog, resolve_applicable_policy, now):
    """An operation marked under the applicable policy reports needs attention."""
    table = _register(tables_repo, now)
    _observe(catalog)
    applied = resolve_applicable_policy.execute(
        ResolveApplicableTableMaintenancePolicyUseCaseInput(
            catalog=KEY[0], table_uuid="u-1", namespace=KEY[1], table=KEY[2]
        )
    )
    mark = AttentionMark(
        since=now,
        reason="out of memory at size L",
        policy=AppliedPolicyRef(name=applied.policy_name, version=applied.version, target=applied.target),
    )
    table.mark_needs_attention(MaintenanceOperation.REWRITE_DATA_FILES, mark, now)
    tables_repo.update(table)
    output = _health(service)
    assert output.operations[0].verdict == "needs_attention"
    assert output.operations[1].verdict != "needs_attention"
