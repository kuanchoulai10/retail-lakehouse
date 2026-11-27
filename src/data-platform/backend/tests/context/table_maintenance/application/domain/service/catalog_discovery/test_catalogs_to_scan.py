"""Test catalogs_to_scan: discovery scans where a policy is placed and where tables are still managed."""

from __future__ import annotations

from context.table_maintenance.application.domain.service.catalog_discovery import catalogs_to_scan


def test_the_catalogs_to_scan_are_the_sorted_union():
    """A catalog with a discovery policy or a managed table is scanned, once, by name."""
    assert catalogs_to_scan(["b"], ["a", "b"]) == ("a", "b")


def test_a_catalog_with_managed_tables_but_no_policy_is_still_scanned():
    """Its scan unmanages the tables no policy manages any more."""
    assert catalogs_to_scan([], ["c"]) == ("c",)


def test_nothing_placed_and_nothing_managed_scans_nothing():
    """No catalog holds a discovery policy or a managed table: none is scanned."""
    assert catalogs_to_scan([], []) == ()
