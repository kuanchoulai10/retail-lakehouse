"""Test the service that seeds the default discovery policy."""

from __future__ import annotations

from datetime import UTC, datetime

from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DEFAULT_DISCOVERY_POLICY_ID,
    DiscoveryPolicyContent,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    EnsureDefaultTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.service.table_discovery_policy import (
    EnsureDefaultTableDiscoveryPolicyService,
)
from tests.context.table_maintenance.fakes.in_memory_table_discovery_policies_repo import (
    InMemoryTableDiscoveryPoliciesRepo,
)

NOW = datetime(2026, 11, 1, tzinfo=UTC)


def test_ensure_default_twice_keeps_one():
    """The first call creates the default and says so; the second finds it and creates nothing."""
    repo = InMemoryTableDiscoveryPoliciesRepo()
    service = EnsureDefaultTableDiscoveryPolicyService(repo, clock=lambda: NOW)

    assert service.execute(EnsureDefaultTableDiscoveryPolicyUseCaseInput()).created is True
    assert service.execute(EnsureDefaultTableDiscoveryPolicyUseCaseInput()).created is False

    policies = repo.list_all()
    assert [(p.id, p.name.value, p.version, p.created_at) for p in policies] == [
        (DEFAULT_DISCOVERY_POLICY_ID, "default", 1, NOW)
    ]
    assert policies[0].content == DiscoveryPolicyContent.platform_default()
    assert repo.get_version(DEFAULT_DISCOVERY_POLICY_ID, 1) is not None
