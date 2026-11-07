"""Samples of the boundary directory rules, checked against table maintenance's tree.

The generic rule in ``tests/architecture/test_import_boundary.py`` only checks
shapes every context has. These samples pin concrete table maintenance packages,
so a change to the boundary derivation shows up against real code.
"""

from __future__ import annotations

from tests.architecture.boundaries import boundaries

CONTEXT = "context.table_maintenance"
GLOBAL_BOUNDARIES = ("base", "bootstrap.configs", "bootstrap.container")
CONTEXT_BOUNDARIES = (
    "application.exceptions",
    "application.domain.model.table",
    "application.port.outbound.table",
    "application.service.shared",
    "adapter.inbound.web",
    "adapter.inbound.web.table",
    "adapter.inbound.web.shared",
    "adapter.inbound.event_consumer",
    "adapter.outbound.table.sql",
    "adapter.outbound.shared.sql",
    "adapter.hybrid.temporal.contracts",
    "adapter.hybrid.temporal.contracts.table_maintenance",
    "adapter.hybrid.temporal.inbound",
    "adapter.hybrid.temporal.inbound.workflows",
    "adapter.hybrid.temporal.outbound.table",
)
CONTEXT_NON_BOUNDARIES = (
    "adapter.outbound.table",
    "application.port.inbound.table.include_table",
)


def test_table_maintenance_boundary_samples():
    known = boundaries()
    for expected in (
        *GLOBAL_BOUNDARIES,
        *(f"{CONTEXT}.{suffix}" for suffix in CONTEXT_BOUNDARIES),
    ):
        assert expected in known, expected
    for not_a_boundary in (
        *(f"{CONTEXT}.{suffix}" for suffix in CONTEXT_NON_BOUNDARIES),
        "bootstrap",
    ):
        assert not_a_boundary not in known, not_a_boundary
