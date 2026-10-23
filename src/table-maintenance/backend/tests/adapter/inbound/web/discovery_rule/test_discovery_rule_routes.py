"""Test the discovery rule routes."""

from __future__ import annotations

from typing import Any

from application.port.inbound.discovery_rule.create_discovery_rule import (
    CreateDiscoveryRuleUseCaseInput,
    CreateDiscoveryRuleUseCaseOutput,
)
from application.port.inbound.discovery_rule.delete_discovery_rule import (
    DeleteDiscoveryRuleUseCaseInput,
    DeleteDiscoveryRuleUseCaseOutput,
)
from application.port.inbound.discovery_rule.list_discovery_rules import (
    ListDiscoveryRulesUseCaseOutput,
    ListDiscoveryRulesUseCaseOutputItem,
)
from application.port.inbound.discovery_rule.update_discovery_rule import (
    UpdateDiscoveryRuleUseCaseInput,
    UpdateDiscoveryRuleUseCaseOutput,
)
from tests.adapter.inbound.web.web_test_support import NOW, StubUseCase, build_client

FIELDS: dict[str, Any] = {
    "id": "r-1",
    "priority": 10,
    "effect": "include",
    "catalog_pattern": "*",
    "namespace_pattern": "sales",
    "table_pattern": "*",
    "template_id": "t-1",
    "enabled": True,
    "created_at": NOW,
    "updated_at": NOW,
}


def test_list_discovery_rules() -> None:
    output = ListDiscoveryRulesUseCaseOutput(
        items=[ListDiscoveryRulesUseCaseOutputItem(**FIELDS)]
    )
    client = build_client(list_discovery_rules=StubUseCase(output))

    response = client.get("/v1/discovery-rules")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "r-1"
    assert response.json()[0]["namespace_pattern"] == "sales"


def test_create_discovery_rule_returns_201() -> None:
    stub = StubUseCase(CreateDiscoveryRuleUseCaseOutput(**FIELDS))
    client = build_client(create_discovery_rule=stub)

    response = client.post(
        "/v1/discovery-rules",
        json={
            "priority": 10,
            "effect": "include",
            "namespace_pattern": "sales",
            "template_id": "t-1",
        },
    )

    assert response.status_code == 201
    assert response.json()["id"] == "r-1"
    assert stub.requests == [
        CreateDiscoveryRuleUseCaseInput(
            priority=10,
            effect="include",
            namespace_pattern="sales",
            template_id="t-1",
        )
    ]


def test_create_discovery_rule_rejects_unknown_key() -> None:
    client = build_client()

    response = client.post(
        "/v1/discovery-rules", json={"priority": 1, "effect": "include", "x": 1}
    )

    assert response.status_code == 422


def test_update_discovery_rule() -> None:
    stub = StubUseCase(UpdateDiscoveryRuleUseCaseOutput(**FIELDS))
    client = build_client(update_discovery_rule=stub)

    response = client.patch(
        "/v1/discovery-rules/r-1", json={"priority": 20, "effect": "exclude"}
    )

    assert response.status_code == 200
    assert stub.requests == [
        UpdateDiscoveryRuleUseCaseInput(id="r-1", priority=20, effect="exclude")
    ]


def test_delete_discovery_rule_returns_204() -> None:
    stub = StubUseCase(DeleteDiscoveryRuleUseCaseOutput())
    client = build_client(delete_discovery_rule=stub)

    response = client.delete("/v1/discovery-rules/r-1")

    assert response.status_code == 204
    assert stub.requests == [DeleteDiscoveryRuleUseCaseInput(id="r-1")]
