"""Build a web client whose policy and mapping routes run the real services on in-memory fakes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.domain.model.table import Table, TableId, TableName
from context.table_maintenance.application.domain.model.table_discovery_rules import TableDiscoveryRuleId
from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePolicyContent
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    EnsureDefaultTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.service.table_maintenance_policy import (
    CreateTableMaintenancePolicyService,
    DeleteTableMaintenancePolicyService,
    EnsureDefaultTableMaintenancePolicyService,
    GetTableMaintenancePolicyService,
    GetTableMaintenancePolicyVersionService,
    ListTableMaintenancePoliciesService,
    UpdateTableMaintenancePolicyService,
)
from context.table_maintenance.application.service.table_maintenance_policy_attachment import (
    AttachTableMaintenancePolicyService,
    DetachTableMaintenancePolicyService,
    ListTableMaintenancePolicyAttachmentsService,
    ResolveApplicableTableMaintenancePolicyService,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import build_client
from tests.context.table_maintenance.fakes.fake_read_table_metadata_gateway import (
    FakeReadTableMetadataGateway,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policies_repo import (
    InMemoryTableMaintenancePoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policy_attachments_repo import (
    InMemoryTableMaintenancePolicyAttachmentsRepo,
)
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo
from tests.context.table_maintenance.fakes.recording_send_table_change_gateway import (
    RecordingSendTableChangeGateway,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def policy_body(**changes: Any) -> dict[str, Any]:  # noqa: ANN401
    """Return the platform default content as a request body, with ``changes`` applied on top."""
    return {**MaintenancePolicyContent.platform_default().to_primitives(), **changes}


class PolicyWebWorld:
    """Hold the fakes behind a client and the client itself; catalog prod holds sales.eu.orders (u-1)."""

    def __init__(self) -> None:
        """Seed the default policy and one managed table, then build the client."""
        self.policies = InMemoryTableMaintenancePoliciesRepo()
        self.attachments = InMemoryTableMaintenancePolicyAttachmentsRepo()
        self.tables = InMemoryTablesRepo()
        self.catalog = FakeReadTableMetadataGateway()
        self.changes = RecordingSendTableChangeGateway()
        EnsureDefaultTableMaintenancePolicyService(self.policies, clock=lambda: NOW).execute(
            EnsureDefaultTableMaintenancePolicyUseCaseInput()
        )
        self.catalog.add_table("prod", "sales.eu", "orders", "u-1")
        self.tables.create(
            Table.register(
                TableId("u-1"),
                TableName(catalog="prod", namespace="sales.eu", table="orders"),
                TableDiscoveryRuleId("r"),
                NOW,
            )
        )
        policies, attachments, tables, catalog, changes = (
            self.policies,
            self.attachments,
            self.tables,
            self.catalog,
            self.changes,
        )
        self.client: TestClient = build_client(
            list_table_maintenance_policies=ListTableMaintenancePoliciesService(policies, attachments),
            create_table_maintenance_policy=CreateTableMaintenancePolicyService(policies, clock=lambda: NOW),
            get_table_maintenance_policy=GetTableMaintenancePolicyService(policies),
            get_table_maintenance_policy_version=GetTableMaintenancePolicyVersionService(policies),
            update_table_maintenance_policy=UpdateTableMaintenancePolicyService(
                policies, attachments, tables, changes, clock=lambda: NOW
            ),
            delete_table_maintenance_policy=DeleteTableMaintenancePolicyService(policies, attachments),
            attach_table_maintenance_policy=AttachTableMaintenancePolicyService(
                policies, attachments, catalog, tables, changes, clock=lambda: NOW
            ),
            detach_table_maintenance_policy=DetachTableMaintenancePolicyService(
                policies, attachments, catalog, tables, changes
            ),
            list_table_maintenance_policy_attachments=ListTableMaintenancePolicyAttachmentsService(
                policies, attachments, catalog, tables
            ),
            resolve_applicable_table_maintenance_policy=ResolveApplicableTableMaintenancePolicyService(
                policies, attachments, catalog, tables
            ),
        )

    def create(self, name: str, **changes: Any) -> dict[str, Any]:  # noqa: ANN401
        """Create a policy through the API and return the response body."""
        response = self.client.post("/v1/maintenance-policies", json={"name": name, **policy_body(**changes)})
        assert response.status_code == 201, response.text
        return response.json()

    def attach(self, name: str, type_: str, path: list[str]) -> Any:  # noqa: ANN401
        """Attach a policy through the API and return the response."""
        return self.client.put(
            f"/v1/maintenance-policies/{name}/mappings", json={"target": {"type": type_, "path": path}}
        )
