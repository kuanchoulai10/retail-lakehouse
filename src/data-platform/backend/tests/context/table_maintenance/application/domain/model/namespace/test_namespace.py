"""Test the Namespace aggregate: the discovery and maintenance policy it holds, one of each."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context.table_maintenance.application.domain.model.namespace import Namespace
from context.table_maintenance.application.domain.model.shared import (
    NamespaceId,
    PolicyNotAttached,
    TableDiscoveryPolicyId,
    TableMaintenancePolicyId,
)

T0 = datetime(2026, 11, 27, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
T2 = T1 + timedelta(hours=1)
SALES = TableDiscoveryPolicyId("dp-00000000000000000000000001")
EVERYTHING = TableDiscoveryPolicyId("dp-00000000000000000000000002")
NIGHTLY = TableMaintenancePolicyId("mp-00000000000000000000000001")
HOURLY = TableMaintenancePolicyId("mp-00000000000000000000000002")
SALES_EU = NamespaceId.of("iceberg", ("sales", "eu"))


def registered() -> Namespace:
    """Provide the namespace sales.eu of catalog iceberg, registered at T0 and holding no policy."""
    return Namespace.register(SALES_EU, T0)


def test_a_registered_namespace_holds_no_policy_at_version_1():
    """A namespace is registered at version 1, with neither a discovery nor a maintenance policy."""
    namespace = registered()
    assert namespace.id == SALES_EU
    assert namespace.discovery_policy_id is None
    assert namespace.maintenance_policy_id is None
    assert namespace.version == 1
    assert namespace.created_at == namespace.updated_at == T0
    assert not namespace.holds_any_policy


def test_a_namespace_names_its_catalog_and_levels():
    """A namespace answers the catalog that holds it and its levels, outermost first."""
    namespace = registered()
    assert namespace.catalog == "iceberg"
    assert namespace.levels == ("sales", "eu")


def test_attach_a_discovery_policy_to_a_namespace_holding_none():
    """Attaching a discovery policy where none is sets it and moves the update time."""
    namespace = registered()
    namespace.attach_discovery_policy(SALES, T1)
    assert namespace.discovery_policy_id == SALES
    assert namespace.updated_at == T1
    assert namespace.holds_any_policy


def test_attach_another_discovery_policy_replaces_the_attached_one():
    """A namespace holds one discovery policy, so attaching another replaces it."""
    namespace = registered()
    namespace.attach_discovery_policy(SALES, T1)
    namespace.attach_discovery_policy(EVERYTHING, T2)
    assert namespace.discovery_policy_id == EVERYTHING
    assert namespace.updated_at == T2


def test_attach_the_attached_discovery_policy_again_changes_nothing():
    """Attaching the policy already attached is a no-op, so the update time stays."""
    namespace = registered()
    namespace.attach_discovery_policy(SALES, T1)
    namespace.attach_discovery_policy(SALES, T2)
    assert namespace.updated_at == T1


def test_detach_the_attached_discovery_policy_clears_it():
    """Detaching the attached discovery policy leaves the namespace without one."""
    namespace = registered()
    namespace.attach_discovery_policy(SALES, T1)
    namespace.detach_discovery_policy(SALES, T2)
    assert namespace.discovery_policy_id is None
    assert namespace.updated_at == T2
    assert not namespace.holds_any_policy


def test_detach_a_discovery_policy_that_is_not_attached_is_refused():
    """Detaching another policy than the attached one raises PolicyNotAttached and changes nothing."""
    namespace = registered()
    namespace.attach_discovery_policy(SALES, T1)
    with pytest.raises(PolicyNotAttached, match=f"{EVERYTHING} is not attached to namespace sales.eu of iceberg"):
        namespace.detach_discovery_policy(EVERYTHING, T2)
    assert namespace.discovery_policy_id == SALES
    assert namespace.updated_at == T1


def test_attach_a_maintenance_policy_to_a_namespace_holding_none():
    """Attaching a maintenance policy where none is sets it."""
    namespace = registered()
    namespace.attach_maintenance_policy(NIGHTLY, T1)
    assert namespace.maintenance_policy_id == NIGHTLY
    assert namespace.updated_at == T1
    assert namespace.holds_any_policy


def test_attach_another_maintenance_policy_replaces_the_attached_one():
    """A namespace holds one maintenance policy, so attaching another replaces it."""
    namespace = registered()
    namespace.attach_maintenance_policy(NIGHTLY, T1)
    namespace.attach_maintenance_policy(HOURLY, T2)
    assert namespace.maintenance_policy_id == HOURLY


def test_detach_the_attached_maintenance_policy_clears_it():
    """Detaching the attached maintenance policy leaves the namespace without one."""
    namespace = registered()
    namespace.attach_maintenance_policy(NIGHTLY, T1)
    namespace.detach_maintenance_policy(NIGHTLY, T2)
    assert namespace.maintenance_policy_id is None
    assert not namespace.holds_any_policy


def test_detach_a_maintenance_policy_that_is_not_attached_is_refused():
    """Detaching another maintenance policy than the attached one raises PolicyNotAttached."""
    namespace = registered()
    namespace.attach_maintenance_policy(NIGHTLY, T1)
    with pytest.raises(PolicyNotAttached):
        namespace.detach_maintenance_policy(HOURLY, T2)
    assert namespace.maintenance_policy_id == NIGHTLY
