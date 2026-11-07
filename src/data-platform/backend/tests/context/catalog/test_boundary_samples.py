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
    "application.domain.service.shared",
    "adapter.inbound.web",
    "adapter.inbound.web.shared",
    "adapter.outbound.shared.polaris",
)
CONTEXT_NON_BOUNDARIES = (
    "adapter.outbound.shared",
    "application.domain.service",
)


def test_catalog_boundary_samples():
    """The expected boundary packages of the context are known and a plain package is not."""
    known = boundaries()
    for expected in (f"{CONTEXT}.{suffix}" for suffix in CONTEXT_BOUNDARIES):
        assert expected in known, expected
    for not_a_boundary in (f"{CONTEXT}.{suffix}" for suffix in CONTEXT_NON_BOUNDARIES):
        assert not_a_boundary not in known, not_a_boundary
