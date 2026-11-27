"""Test the Catalog aggregate: the discovery and maintenance policy it holds, one of each."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.catalog import Catalog
from context.table_maintenance.application.domain.model.shared import (
    CatalogId,
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


def registered() -> Catalog:
    """Provide a catalog registered at T0, holding no policy."""
    return Catalog.register(CatalogId("iceberg"), T0)


def test_a_registered_catalog_holds_no_policy_at_version_1():
    """A catalog is registered at version 1, with neither a discovery nor a maintenance policy."""
    catalog = registered()
    assert catalog.id == CatalogId("iceberg")
    assert catalog.discovery_policy_id is None
    assert catalog.maintenance_policy_id is None
    assert catalog.version == 1
    assert catalog.created_at == catalog.updated_at == T0
    assert not catalog.holds_any_policy


def test_a_catalog_needs_a_name():
    """A catalog id is the catalog's name, so an empty one is refused."""
    with pytest.raises(InvariantViolation, match="catalog needs a name"):
        Catalog.register(CatalogId(""), T0)


def test_attach_a_discovery_policy_to_a_catalog_holding_none():
    """Attaching a discovery policy where none is sets it and moves the update time."""
    catalog = registered()
    catalog.attach_discovery_policy(SALES, T1)
    assert catalog.discovery_policy_id == SALES
    assert catalog.maintenance_policy_id is None
    assert catalog.updated_at == T1
    assert catalog.holds_any_policy


def test_attach_another_discovery_policy_replaces_the_attached_one():
    """A catalog holds one discovery policy, so attaching another replaces it."""
    catalog = registered()
    catalog.attach_discovery_policy(SALES, T1)
    catalog.attach_discovery_policy(EVERYTHING, T2)
    assert catalog.discovery_policy_id == EVERYTHING
    assert catalog.updated_at == T2


def test_attach_the_attached_discovery_policy_again_changes_nothing():
    """Attaching the policy already attached is a no-op, so the update time stays."""
    catalog = registered()
    catalog.attach_discovery_policy(SALES, T1)
    catalog.attach_discovery_policy(SALES, T2)
    assert catalog.discovery_policy_id == SALES
    assert catalog.updated_at == T1


def test_detach_the_attached_discovery_policy_clears_it():
    """Detaching the attached discovery policy leaves the catalog without one."""
    catalog = registered()
    catalog.attach_discovery_policy(SALES, T1)
    catalog.detach_discovery_policy(SALES, T2)
    assert catalog.discovery_policy_id is None
    assert catalog.updated_at == T2
    assert not catalog.holds_any_policy


def test_detach_a_discovery_policy_that_is_not_attached_is_refused():
    """Detaching another policy than the attached one raises PolicyNotAttached and changes nothing."""
    catalog = registered()
    catalog.attach_discovery_policy(SALES, T1)
    with pytest.raises(PolicyNotAttached, match=f"{EVERYTHING} is not attached to catalog iceberg"):
        catalog.detach_discovery_policy(EVERYTHING, T2)
    assert catalog.discovery_policy_id == SALES
    assert catalog.updated_at == T1


def test_detach_a_discovery_policy_from_a_catalog_holding_none_is_refused():
    """A catalog holding no discovery policy refuses any detach."""
    with pytest.raises(PolicyNotAttached):
        registered().detach_discovery_policy(SALES, T1)


def test_attach_a_maintenance_policy_to_a_catalog_holding_none():
    """Attaching a maintenance policy where none is sets it, beside the discovery policy."""
    catalog = registered()
    catalog.attach_discovery_policy(SALES, T1)
    catalog.attach_maintenance_policy(NIGHTLY, T2)
    assert catalog.maintenance_policy_id == NIGHTLY
    assert catalog.discovery_policy_id == SALES
    assert catalog.updated_at == T2


def test_attach_another_maintenance_policy_replaces_the_attached_one():
    """A catalog holds one maintenance policy, so attaching another replaces it."""
    catalog = registered()
    catalog.attach_maintenance_policy(NIGHTLY, T1)
    catalog.attach_maintenance_policy(HOURLY, T2)
    assert catalog.maintenance_policy_id == HOURLY


def test_attach_the_attached_maintenance_policy_again_changes_nothing():
    """Attaching the maintenance policy already attached is a no-op."""
    catalog = registered()
    catalog.attach_maintenance_policy(NIGHTLY, T1)
    catalog.attach_maintenance_policy(NIGHTLY, T2)
    assert catalog.updated_at == T1


def test_detach_the_attached_maintenance_policy_clears_it():
    """Detaching the attached maintenance policy leaves the catalog without one."""
    catalog = registered()
    catalog.attach_maintenance_policy(NIGHTLY, T1)
    assert catalog.holds_any_policy
    catalog.detach_maintenance_policy(NIGHTLY, T2)
    assert catalog.maintenance_policy_id is None
    assert catalog.updated_at == T2
    assert not catalog.holds_any_policy


def test_detach_a_maintenance_policy_that_is_not_attached_is_refused():
    """Detaching another maintenance policy than the attached one raises PolicyNotAttached."""
    catalog = registered()
    catalog.attach_maintenance_policy(NIGHTLY, T1)
    with pytest.raises(PolicyNotAttached, match=f"{HOURLY} is not attached to catalog iceberg"):
        catalog.detach_maintenance_policy(HOURLY, T2)
    assert catalog.maintenance_policy_id == NIGHTLY
    assert catalog.updated_at == T1


def test_policy_not_attached_is_a_value_error():
    """PolicyNotAttached is a ValueError, so the application translates it like other refused domain changes."""
    assert issubclass(PolicyNotAttached, ValueError)
