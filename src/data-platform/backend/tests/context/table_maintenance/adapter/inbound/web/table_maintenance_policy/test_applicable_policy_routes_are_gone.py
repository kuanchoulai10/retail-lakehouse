"""Test that the applicable-policy routes, replaced by effective-policies, are no longer served."""

from __future__ import annotations

import pytest

from tests.context.table_maintenance.adapter.inbound.web.policy_web_world import PolicyWebWorld


@pytest.mark.parametrize("url", ["/v1/tables/u-1/applicable-policy", "/v1/applicable-policy?catalog=prod"])
def test_applicable_policy_routes_are_gone(url: str) -> None:
    """An old client still calling ``applicable-policy`` is told 404, not answered."""
    world = PolicyWebWorld()
    world.create("gold")
    world.attach("gold", "catalog", ["prod"])

    assert world.client.get(url).status_code == 404
