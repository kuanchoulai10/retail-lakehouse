"""Samples of the boundary directory rules, checked against the catalog context's tree.

The generic rule in ``tests/architecture/test_import_boundary.py`` only checks
shapes every context has. These samples pin concrete catalog packages, so a
change to the boundary derivation shows up against real code.
"""

from __future__ import annotations

from tests.architecture.boundaries import boundaries

CONTEXT = "context.catalog"
CONTEXT_BOUNDARIES = (
    "application.exceptions",
    "application.domain.model.catalog",
    "application.port.inbound.catalog",
    "application.port.outbound.catalog",
    "application.service.catalog",
    "application.domain.service.shared",
    "adapter.inbound.web",
    "adapter.inbound.web.shared",
    "adapter.inbound.web.catalog",
    "adapter.outbound.shared.polaris",
    "adapter.outbound.catalog.polaris",
)
CONTEXT_NON_BOUNDARIES = (
    "adapter.outbound.shared",
    "adapter.outbound.catalog",
    "application.port.inbound.catalog.create_catalog",
    "application.port.outbound.catalog.create_catalog_content_grant",
    "application.domain.service",
)


def test_catalog_boundary_samples():
    """The expected boundary packages of the context are known and a plain package is not."""
    known = boundaries()
    for expected in (f"{CONTEXT}.{suffix}" for suffix in CONTEXT_BOUNDARIES):
        assert expected in known, expected
    for not_a_boundary in (f"{CONTEXT}.{suffix}" for suffix in CONTEXT_NON_BOUNDARIES):
        assert not_a_boundary not in known, not_a_boundary
