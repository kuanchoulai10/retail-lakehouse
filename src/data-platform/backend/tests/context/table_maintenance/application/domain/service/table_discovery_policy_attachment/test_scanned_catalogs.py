"""Test scanned_catalogs: a catalog is scanned when one of its attachments points at a policy that can manage."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table import TableName
from context.table_maintenance.application.domain.service.table_discovery_policy_attachment import (
    scanned_catalogs,
)
from tests.context.table_maintenance.application.domain.service.table_discovery_policy_attachment.discovery_policy_samples import (  # noqa: E501
    DEFAULT,
    MANAGE_ALL,
    MANAGE_BY_DEFAULT,
    POLICIES,
    attached,
    catalog_target,
    namespace_target,
    table_target,
)


def test_a_catalog_is_scanned_when_a_policy_in_it_can_manage():
    """A namespace attachment of a managing rule scans its catalog; a catalog holding only the default is not."""
    assert scanned_catalogs(
        [attached(namespace_target("iceberg", "sales"), MANAGE_ALL), attached(catalog_target("other"), DEFAULT)],
        {MANAGE_ALL.id: MANAGE_ALL, DEFAULT.id: DEFAULT},
    ) == ("iceberg",)


def test_a_no_match_outcome_of_manage_scans_the_catalog():
    """A policy with no rule that manages everything it does not match can manage."""
    assert scanned_catalogs([attached(catalog_target("iceberg"), MANAGE_BY_DEFAULT)], POLICIES) == ("iceberg",)


def test_a_table_attachment_scans_its_catalog():
    """A table attachment's catalog is the first element of its path."""
    attachment = attached(
        table_target(TableName(catalog="iceberg", namespace="sales", table="orders"), "u1"), MANAGE_ALL
    )

    assert scanned_catalogs([attachment], POLICIES) == ("iceberg",)


def test_scanned_catalogs_are_sorted_and_unique():
    """Each catalog is listed once, by name, however many managing attachments it holds and in whatever order."""
    attachments = [
        attached(catalog_target("zeta"), MANAGE_ALL),
        attached(namespace_target("theta", "sales"), MANAGE_BY_DEFAULT),
        attached(catalog_target("mid"), DEFAULT),
        attached(catalog_target("kappa"), MANAGE_ALL),
        attached(namespace_target("zeta", "hr"), MANAGE_BY_DEFAULT),
        attached(catalog_target("gamma"), MANAGE_ALL),
        attached(namespace_target("delta", "sales.eu"), MANAGE_ALL),
        attached(catalog_target("beta"), MANAGE_BY_DEFAULT),
        attached(namespace_target("alpha", "sales"), MANAGE_ALL),
        attached(catalog_target("alpha"), MANAGE_BY_DEFAULT),
    ]

    assert scanned_catalogs(attachments, POLICIES) == ("alpha", "beta", "delta", "gamma", "kappa", "theta", "zeta")


def test_an_attachment_without_its_policy_scans_nothing():
    """An attachment whose policy is gone (a race with its delete) is skipped."""
    assert scanned_catalogs([attached(catalog_target("iceberg"), MANAGE_ALL)], {}) == ()


def test_nothing_attached_scans_nothing():
    """With no attachment no catalog is scanned."""
    assert scanned_catalogs([], POLICIES) == ()
