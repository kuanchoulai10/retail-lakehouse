"""Pin that the one discovery rules list is gone; discovery policies replace it."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.context.table_maintenance.adapter.inbound.web.discovery_policy_web_world import DiscoveryPolicyWebWorld

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """Provide a client over the default discovery policy."""
    return DiscoveryPolicyWebWorld().client


def test_discovery_rules_routes_are_gone(client: TestClient) -> None:
    """GET /v1/discovery-rules and GET /v1/discovery-rules/catalogs are not routes any more."""
    assert client.get("/v1/discovery-rules").status_code == 404
    assert client.get("/v1/discovery-rules/catalogs").status_code == 404
