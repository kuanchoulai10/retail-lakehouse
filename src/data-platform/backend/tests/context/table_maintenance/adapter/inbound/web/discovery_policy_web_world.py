"""Build a web client whose discovery policy routes run the real services on in-memory fakes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.service.catalog_discovery import ListScannedCatalogsService
from context.table_maintenance.application.service.table_discovery_policy import (
    AttachTableDiscoveryPolicyService,
    CreateTableDiscoveryPolicyService,
    DeleteTableDiscoveryPolicyService,
    DetachTableDiscoveryPolicyService,
    GetTableDiscoveryPolicyService,
    GetTableDiscoveryPolicyVersionService,
    ListTableDiscoveryPoliciesService,
    ListTableDiscoveryPolicyAttachmentsService,
    UpdateTableDiscoveryPolicyService,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import build_client
from tests.context.table_maintenance.fakes.fake_read_table_metadata_gateway import FakeReadTableMetadataGateway
from tests.context.table_maintenance.fakes.in_memory_catalog_discoveries_repo import InMemoryCatalogDiscoveriesRepo
from tests.context.table_maintenance.fakes.in_memory_catalogs_repo import InMemoryCatalogsRepo
from tests.context.table_maintenance.fakes.in_memory_namespaces_repo import InMemoryNamespacesRepo
from tests.context.table_maintenance.fakes.in_memory_policy_placements_store import InMemoryPolicyPlacementsStore
from tests.context.table_maintenance.fakes.in_memory_table_discovery_policies_repo import (
    InMemoryTableDiscoveryPoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo
from tests.context.table_maintenance.fakes.recording_send_discovery_request_gateway import (
    RecordingSendDiscoveryRequestGateway,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

NOW = datetime(2026, 11, 1, tzinfo=UTC)


def discovery_rule(pattern: str = "orders_*", action: str = "include", **extra: Any) -> dict[str, Any]:  # noqa: ANN401
    """Return a rule body that includes (or ``action``) the tables whose name matches ``pattern``."""
    return {"action": action, "table_name_pattern": pattern, **extra}


def discovery_policy_body(*rules: dict[str, Any], **changes: Any) -> dict[str, Any]:  # noqa: ANN401
    """Return a body holding ``rules`` (one include of ``orders_*`` when none is given), with ``changes`` on top."""
    return {"description": "", "rules": list(rules or (discovery_rule(),)), **changes}


class DiscoveryPolicyWebWorld:
    """Hold the fakes behind a client and the client itself; no policy is stored at first.

    The catalog gateway starts empty: a test adds the catalogs, namespaces and tables it attaches to.
    """

    def __init__(self) -> None:
        """Build the fakes, then the client."""
        self.catalogs = InMemoryCatalogsRepo()
        self.namespaces = InMemoryNamespacesRepo()
        self.tables = InMemoryTablesRepo()
        self.placements = InMemoryPolicyPlacementsStore(self.catalogs, self.namespaces, self.tables)
        self.policies = InMemoryTableDiscoveryPoliciesRepo()
        self.catalog = FakeReadTableMetadataGateway()
        self.discoveries = InMemoryCatalogDiscoveriesRepo()
        self.requests = RecordingSendDiscoveryRequestGateway()
        policies, placements, requests = self.policies, self.placements, self.requests
        places = (self.catalogs, self.namespaces, self.tables)
        self.client: TestClient = build_client(
            list_table_discovery_policies=ListTableDiscoveryPoliciesService(policies, placements),
            create_table_discovery_policy=CreateTableDiscoveryPolicyService(policies, clock=lambda: NOW),
            get_table_discovery_policy=GetTableDiscoveryPolicyService(policies),
            get_table_discovery_policy_version=GetTableDiscoveryPolicyVersionService(policies),
            update_table_discovery_policy=UpdateTableDiscoveryPolicyService(
                policies, placements, requests, clock=lambda: NOW
            ),
            delete_table_discovery_policy=DeleteTableDiscoveryPolicyService(policies, placements),
            attach_table_discovery_policy=AttachTableDiscoveryPolicyService(
                policies, *places, self.catalog, requests, clock=lambda: NOW
            ),
            detach_table_discovery_policy=DetachTableDiscoveryPolicyService(
                policies, *places, requests, clock=lambda: NOW
            ),
            list_table_discovery_policy_attachments=ListTableDiscoveryPolicyAttachmentsService(
                policies, placements, self.catalog, self.tables
            ),
            list_scanned_catalogs=ListScannedCatalogsService(placements, self.tables, self.discoveries),
        )

    def create(self, name: str, *rules: dict[str, Any], **changes: Any) -> dict[str, Any]:  # noqa: ANN401
        """Create a policy through the API and return the response body."""
        response = self.client.post(
            "/v1/discovery-policies", json={"name": name, **discovery_policy_body(*rules, **changes)}
        )
        assert response.status_code == 201, response.text
        return response.json()

    def update(self, name: str, version: int, *rules: dict[str, Any], **changes: Any) -> Any:  # noqa: ANN401
        """Revise a policy's description and rules through the API and return the response."""
        return self.client.put(
            f"/v1/discovery-policies/{name}", json={"version": version, **discovery_policy_body(*rules, **changes)}
        )

    def attach(self, name: str, type_: str, path: list[str]) -> Any:  # noqa: ANN401
        """Attach a policy to a target through the API and return the response."""
        return self.client.put(
            f"/v1/discovery-policies/{name}/attachments", json={"target": {"type": type_, "path": path}}
        )

    def detach(self, name: str, type_: str, path: list[str]) -> Any:  # noqa: ANN401
        """Detach a policy from the place ``type_`` and ``path`` name through the API and return the response."""
        return self.client.delete(
            f"/v1/discovery-policies/{name}/attachments", params={"target_type": type_, "path": path}
        )
