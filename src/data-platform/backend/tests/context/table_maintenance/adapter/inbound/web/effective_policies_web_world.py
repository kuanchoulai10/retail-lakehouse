"""Build a web client whose attach and effective-policies routes run the real services on in-memory fakes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.domain.model.shared import TableId
from context.table_maintenance.application.domain.model.table import Table, TableName
from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePolicyContent
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    CreateTableDiscoveryPolicyUseCaseInput,
    UpdateTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    CreateTableMaintenancePolicyUseCaseInput,
    EnsureDefaultTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.service.table import GetEffectivePoliciesService, GetTableService
from context.table_maintenance.application.service.table_discovery_policy import (
    CreateTableDiscoveryPolicyService,
    UpdateTableDiscoveryPolicyService,
)
from context.table_maintenance.application.service.table_discovery_policy_attachment import (
    AttachTableDiscoveryPolicyService,
)
from context.table_maintenance.application.service.table_maintenance_policy import (
    CreateTableMaintenancePolicyService,
    EnsureDefaultTableMaintenancePolicyService,
)
from context.table_maintenance.application.service.table_maintenance_policy_attachment import (
    AttachTableMaintenancePolicyService,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import build_client
from tests.context.table_maintenance.discovery_decision_samples import MANAGED
from tests.context.table_maintenance.fakes.fake_read_table_metadata_gateway import FakeReadTableMetadataGateway
from tests.context.table_maintenance.fakes.in_memory_catalog_discoveries_repo import InMemoryCatalogDiscoveriesRepo
from tests.context.table_maintenance.fakes.in_memory_table_discovery_policies_repo import (
    InMemoryTableDiscoveryPoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_discovery_policy_attachments_repo import (
    InMemoryTableDiscoveryPolicyAttachmentsRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policies_repo import (
    InMemoryTableMaintenancePoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policy_attachments_repo import (
    InMemoryTableMaintenancePolicyAttachmentsRepo,
)
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo
from tests.context.table_maintenance.fakes.recording_send_discovery_request_gateway import (
    RecordingSendDiscoveryRequestGateway,
)
from tests.context.table_maintenance.fakes.recording_send_table_change_gateway import (
    RecordingSendTableChangeGateway,
)
from tests.context.table_maintenance.fakes.recording_sync_discovery_schedules_gateway import (
    RecordingSyncDiscoverySchedulesGateway,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

NOW = datetime(2026, 11, 1, tzinfo=UTC)
SALES_TABLES_RULES = ({"action": "include", "table_name_pattern": "*"},)


class EffectivePoliciesWebWorld:
    """Hold the fakes of both kinds of policy behind a client, and the client.

    Catalog ``prod`` holds ``sales.eu.orders`` (uuid ``u-1``, recorded by table maintenance) and
    ``sales.eu.returns`` (uuid ``u-2``, not recorded). Maintenance policy ``gold`` and discovery policy
    ``sales-tables`` exist beside the platform's maintenance default; there is no discovery default.
    """

    def __init__(self) -> None:
        """Seed the maintenance default, one policy of each kind and the catalog, then build the client."""
        self.maintenance_policies = InMemoryTableMaintenancePoliciesRepo()
        self.maintenance_attachments = InMemoryTableMaintenancePolicyAttachmentsRepo()
        self.discovery_attachments = InMemoryTableDiscoveryPolicyAttachmentsRepo()
        self.discovery_policies = InMemoryTableDiscoveryPoliciesRepo(attachments=self.discovery_attachments)
        self.catalog = FakeReadTableMetadataGateway()
        self.tables = InMemoryTablesRepo()
        EnsureDefaultTableMaintenancePolicyService(self.maintenance_policies, clock=lambda: NOW).execute(
            EnsureDefaultTableMaintenancePolicyUseCaseInput()
        )
        CreateTableMaintenancePolicyService(self.maintenance_policies, clock=lambda: NOW).execute(
            CreateTableMaintenancePolicyUseCaseInput(
                name="gold", content={**MaintenancePolicyContent.platform_default().to_primitives(), "dry_run": True}
            )
        )
        CreateTableDiscoveryPolicyService(self.discovery_policies, clock=lambda: NOW).execute(
            CreateTableDiscoveryPolicyUseCaseInput(
                name="sales-tables", description="Sales tables", rules=SALES_TABLES_RULES
            )
        )
        self.catalog.add_table("prod", "sales.eu", "orders", "u-1")
        self.catalog.add_table("prod", "sales.eu", "returns", "u-2")
        self.tables.create(
            Table.register(
                TableId("u-1"), TableName(catalog="prod", namespace="sales.eu", table="orders"), MANAGED, NOW
            )
        )
        self.client: TestClient = build_client(
            attach_table_maintenance_policy=AttachTableMaintenancePolicyService(
                self.maintenance_policies,
                self.maintenance_attachments,
                self.catalog,
                self.tables,
                RecordingSendTableChangeGateway(),
                clock=lambda: NOW,
            ),
            attach_table_discovery_policy=AttachTableDiscoveryPolicyService(
                self.discovery_policies,
                self.discovery_attachments,
                self.catalog,
                RecordingSendDiscoveryRequestGateway(),
                RecordingSyncDiscoverySchedulesGateway(),
                clock=lambda: NOW,
            ),
            get_table=GetTableService(self.tables, InMemoryCatalogDiscoveriesRepo(), self.maintenance_policies),
            get_effective_policies=GetEffectivePoliciesService(
                self.maintenance_policies,
                self.maintenance_attachments,
                self.discovery_policies,
                self.discovery_attachments,
                self.catalog,
                self.tables,
            ),
        )

    def attach_maintenance(self, name: str, type_: str, path: list[str]) -> dict[str, Any]:
        """Attach a maintenance policy through the API and return the response body."""
        response = self.client.put(
            f"/v1/maintenance-policies/{name}/attachments", json={"target": {"type": type_, "path": path}}
        )
        assert response.status_code == 200, response.text
        return response.json()

    def attach_discovery(self, name: str, type_: str, path: list[str]) -> dict[str, Any]:
        """Attach a discovery policy through the API and return the response body."""
        response = self.client.put(
            f"/v1/discovery-policies/{name}/attachments", json={"target": {"type": type_, "path": path}}
        )
        assert response.status_code == 200, response.text
        return response.json()

    def update_discovery(self, name: str, version: int, description: str) -> None:
        """Revise a discovery policy as its next version with a new description and the same rules."""
        UpdateTableDiscoveryPolicyService(
            self.discovery_policies,
            self.discovery_attachments,
            RecordingSendDiscoveryRequestGateway(),
            RecordingSyncDiscoverySchedulesGateway(),
            clock=lambda: NOW,
        ).execute(
            UpdateTableDiscoveryPolicyUseCaseInput(
                name=name, description=description, rules=SALES_TABLES_RULES, version=version
            )
        )
