"""Build a web client whose discovery policy routes run the real services on in-memory fakes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    EnsureDefaultTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.service.table_discovery_policy import (
    CreateTableDiscoveryPolicyService,
    DeleteTableDiscoveryPolicyService,
    EnsureDefaultTableDiscoveryPolicyService,
    GetTableDiscoveryPolicyService,
    GetTableDiscoveryPolicyVersionService,
    ListTableDiscoveryPoliciesService,
    UpdateTableDiscoveryPolicyService,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import build_client
from tests.context.table_maintenance.fakes.in_memory_table_discovery_policies_repo import (
    InMemoryTableDiscoveryPoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_discovery_policy_attachments_repo import (
    InMemoryTableDiscoveryPolicyAttachmentsRepo,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

NOW = datetime(2026, 11, 1, tzinfo=UTC)


def discovery_rule(*globs: str, outcome: str = "manage", **extra: Any) -> dict[str, Any]:  # noqa: ANN401
    """Return a rule body matching the table names ``globs`` (``orders_*`` when none is given)."""
    return {
        "outcome": outcome,
        "conditions": [{"attribute": "table_name", "operator": "glob", "values": list(globs or ("orders_*",))}],
        **extra,
    }


def discovery_policy_body(*rules: dict[str, Any], **changes: Any) -> dict[str, Any]:  # noqa: ANN401
    """Return a content body holding ``rules``, unmanaging what no rule matches, with ``changes`` on top."""
    return {"description": "", "no_match_outcome": "unmanage", "rules": list(rules), **changes}


class DiscoveryPolicyWebWorld:
    """Hold the fakes behind a client and the client itself; only the default policy is stored at first."""

    def __init__(self) -> None:
        """Seed the default discovery policy, then build the client."""
        self.attachments = InMemoryTableDiscoveryPolicyAttachmentsRepo()
        self.policies = InMemoryTableDiscoveryPoliciesRepo(attachments=self.attachments)
        EnsureDefaultTableDiscoveryPolicyService(self.policies, clock=lambda: NOW).execute(
            EnsureDefaultTableDiscoveryPolicyUseCaseInput()
        )
        policies, attachments = self.policies, self.attachments
        self.client: TestClient = build_client(
            list_table_discovery_policies=ListTableDiscoveryPoliciesService(policies, attachments),
            create_table_discovery_policy=CreateTableDiscoveryPolicyService(policies, clock=lambda: NOW),
            get_table_discovery_policy=GetTableDiscoveryPolicyService(policies),
            get_table_discovery_policy_version=GetTableDiscoveryPolicyVersionService(policies),
            update_table_discovery_policy=UpdateTableDiscoveryPolicyService(policies, clock=lambda: NOW),
            delete_table_discovery_policy=DeleteTableDiscoveryPolicyService(policies, attachments),
        )

    def create(self, name: str, *rules: dict[str, Any], **changes: Any) -> dict[str, Any]:  # noqa: ANN401
        """Create a policy through the API and return the response body."""
        response = self.client.post(
            "/v1/discovery-policies", json={"name": name, **discovery_policy_body(*rules, **changes)}
        )
        assert response.status_code == 201, response.text
        return response.json()

    def update(self, name: str, version: int, *rules: dict[str, Any], **changes: Any) -> Any:  # noqa: ANN401
        """Replace a policy's content through the API and return the response."""
        return self.client.put(
            f"/v1/discovery-policies/{name}", json={"version": version, **discovery_policy_body(*rules, **changes)}
        )
