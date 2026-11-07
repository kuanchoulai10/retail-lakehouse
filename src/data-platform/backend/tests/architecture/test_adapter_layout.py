"""Guard test: adapter/ is split into inbound, outbound and hybrid technologies."""

from __future__ import annotations

import pytest

from tests.architecture.contexts import context_dir, context_names
from tests.architecture.test_aggregate_axis import subdirs


@pytest.mark.parametrize("context", context_names())
def test_adapter_top_level(context: str):
    """The adapter directory of a context holds only the inbound, outbound and hybrid directions."""
    assert subdirs(context_dir(context) / "adapter") == {
        "inbound",
        "outbound",
        "hybrid",
    }


@pytest.mark.parametrize("context", context_names())
def test_hybrid_tech_has_both_directions(context: str):
    """Each hybrid technology directory splits into an inbound and an outbound side."""
    hybrid = context_dir(context) / "adapter" / "hybrid"
    for tech in subdirs(hybrid):
        assert subdirs(hybrid / tech) == {
            "inbound",
            "outbound",
            "contracts",
        }, f"{hybrid / tech} must hold exactly inbound, outbound, contracts"
