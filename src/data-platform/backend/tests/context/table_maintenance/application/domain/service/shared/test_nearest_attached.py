"""Test the nearest_attached domain service."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table import TableName
from context.table_maintenance.application.domain.service.shared import (
    candidate_policy_targets,
    nearest_attached,
)

ORDERS = TableName(catalog="iceberg", namespace="sales", table="orders")


def test_nearest_attached_prefers_the_first_candidate_that_is_attached():
    """The namespace is nearer than the catalog, so its attachment wins."""
    table, ns, catalog = candidate_policy_targets(ORDERS, "u1")
    assert nearest_attached((table, ns, catalog), {ns.key(): "A", catalog.key(): "B"}) == (ns, "A")


def test_nearest_attached_takes_the_table_over_its_parents():
    """A table's own attachment beats every attachment above it."""
    table, ns, catalog = candidate_policy_targets(ORDERS, "u1")
    attached = {catalog.key(): "C", ns.key(): "N", table.key(): "T"}
    assert nearest_attached((table, ns, catalog), attached) == (table, "T")


def test_nearest_attached_falls_through_to_the_catalog():
    """With only the catalog attached, the catalog decides."""
    candidates = candidate_policy_targets(ORDERS, "u1")
    catalog = candidates[-1]
    assert nearest_attached(candidates, {catalog.key(): "C"}) == (catalog, "C")


def test_nearest_attached_is_none_when_nothing_is_attached():
    """No attachment among the candidates is None."""
    assert nearest_attached(candidate_policy_targets(ORDERS, "u1"), {}) is None


def test_nearest_attached_ignores_attachments_off_the_walk():
    """An attachment on another namespace is not among the candidates and is never picked."""
    other = candidate_policy_targets(TableName(catalog="iceberg", namespace="hr", table="staff"), "u2")
    assert nearest_attached(candidate_policy_targets(ORDERS, "u1"), {other[1].key(): "X"}) is None
