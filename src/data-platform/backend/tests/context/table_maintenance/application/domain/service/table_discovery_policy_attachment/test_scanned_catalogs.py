"""Test scanned_catalogs: a catalog is scanned when a discovery policy is attached in it."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table import TableName
from context.table_maintenance.application.domain.service.table_discovery_policy_attachment import (
    scanned_catalogs,
)
from tests.context.table_maintenance.application.domain.service.table_discovery_policy_attachment.discovery_policy_samples import (  # noqa: E501
    MANAGE_ALL,
    MANAGE_ORDERS,
    POLICIES,
    UNMANAGE_ALL,
    attached,
    catalog_target,
    namespace_target,
    table_target,
)


def test_every_catalog_with_an_attachment_is_scanned_whatever_the_policy_holds():
    """An include policy and an exclude-only policy both scan their catalog."""
    assert scanned_catalogs(
        [attached(namespace_target("iceberg", "sales"), MANAGE_ALL), attached(catalog_target("other"), UNMANAGE_ALL)],
        POLICIES,
    ) == ("iceberg", "other")


def test_an_exclude_only_policy_scans_its_catalog():
    """A policy that can only exclude still scans, so the tables it now excludes are unmanaged."""
    assert scanned_catalogs([attached(catalog_target("iceberg"), UNMANAGE_ALL)], POLICIES) == ("iceberg",)


def test_a_table_attachment_scans_its_catalog():
    """A table attachment's catalog is the first element of its path."""
    attachment = attached(
        table_target(TableName(catalog="iceberg", namespace="sales", table="orders"), "u1"), MANAGE_ORDERS
    )

    assert scanned_catalogs([attachment], POLICIES) == ("iceberg",)


def test_scanned_catalogs_are_sorted_and_unique():
    """Each catalog is listed once, by name, however many attachments it holds and in whatever order."""
    attachments = [
        attached(catalog_target("zeta"), MANAGE_ALL),
        attached(namespace_target("theta", "sales"), MANAGE_ORDERS),
        attached(catalog_target("mid"), UNMANAGE_ALL),
        attached(catalog_target("kappa"), MANAGE_ALL),
        attached(namespace_target("zeta", "hr"), MANAGE_ORDERS),
        attached(catalog_target("gamma"), MANAGE_ALL),
        attached(namespace_target("delta", "sales.eu"), MANAGE_ALL),
        attached(catalog_target("beta"), MANAGE_ORDERS),
        attached(namespace_target("alpha", "sales"), MANAGE_ALL),
        attached(catalog_target("alpha"), MANAGE_ORDERS),
    ]

    assert scanned_catalogs(attachments, POLICIES) == (
        "alpha",
        "beta",
        "delta",
        "gamma",
        "kappa",
        "mid",
        "theta",
        "zeta",
    )


def test_an_attachment_without_its_policy_scans_nothing():
    """An attachment whose policy is gone (a race with its delete) is skipped."""
    assert scanned_catalogs([attached(catalog_target("iceberg"), MANAGE_ALL)], {}) == ()


def test_nothing_attached_scans_nothing():
    """With no attachment no catalog is scanned."""
    assert scanned_catalogs([], POLICIES) == ()
