"""Guard test: adapter/ is split into inbound, outbound and hybrid technologies."""

from __future__ import annotations

from tests.architecture.test_aggregate_axis import subdirs


def test_adapter_top_level():
    assert subdirs("context/table_maintenance/adapter") == {
        "inbound",
        "outbound",
        "hybrid",
    }


def test_hybrid_tech_has_both_directions():
    for tech in subdirs("context/table_maintenance/adapter/hybrid"):
        assert subdirs(f"context/table_maintenance/adapter/hybrid/{tech}") == {
            "inbound",
            "outbound",
            "contracts",
        }, (
            f"context/table_maintenance/adapter/hybrid/{tech} must hold exactly inbound, outbound, contracts"
        )
