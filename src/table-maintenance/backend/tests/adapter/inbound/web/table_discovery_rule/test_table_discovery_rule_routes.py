"""Test the discovery rule routes."""

from __future__ import annotations

from typing import Any

from application.port.inbound.table_discovery_rule.create_table_discovery_rule import (
    CreateTableDiscoveryRuleUseCaseInput,
    CreateTableDiscoveryRuleUseCaseOutput,
)
from application.port.inbound.table_discovery_rule.delete_table_discovery_rule import (
    DeleteTableDiscoveryRuleUseCaseInput,
    DeleteTableDiscoveryRuleUseCaseOutput,
)
from application.port.inbound.table_discovery_rule.list_table_discovery_rules import (
    ListTableDiscoveryRulesUseCaseOutput,
    ListTableDiscoveryRulesUseCaseOutputItem,
)
from application.port.inbound.table_discovery_rule.update_table_discovery_rule import (
    UpdateTableDiscoveryRuleUseCaseInput,
    UpdateTableDiscoveryRuleUseCaseOutput,
)
from tests.adapter.inbound.web.web_test_support import NOW, StubUseCase, build_client

FIELDS: dict[str, Any] = {
    "id": "r-1",
    "priority": 10,
    "effect": "include",
    "catalog_pattern": "*",
    "namespace_pattern": "sales",
    "table_pattern": "*",
    "preset_id": "t-1",
    "enabled": True,
    "created_at": NOW,
    "updated_at": NOW,
}


def test_list_table_discovery_rules() -> None:
    output = ListTableDiscoveryRulesUseCaseOutput(
        items=[ListTableDiscoveryRulesUseCaseOutputItem(**FIELDS)]
    )
    client = build_client(list_table_discovery_rules=StubUseCase(output))

    response = client.get("/v1/table-discovery-rules")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "r-1"
    assert response.json()[0]["namespace_pattern"] == "sales"


def test_create_table_discovery_rule_returns_201() -> None:
    stub = StubUseCase(CreateTableDiscoveryRuleUseCaseOutput(**FIELDS))
    client = build_client(create_table_discovery_rule=stub)

    response = client.post(
        "/v1/table-discovery-rules",
        json={
            "priority": 10,
            "effect": "include",
            "namespace_pattern": "sales",
            "preset_id": "t-1",
        },
    )

    assert response.status_code == 201
    assert response.json()["id"] == "r-1"
    assert stub.requests == [
        CreateTableDiscoveryRuleUseCaseInput(
            priority=10,
            effect="include",
            namespace_pattern="sales",
            preset_id="t-1",
        )
    ]


def test_create_table_discovery_rule_rejects_unknown_key() -> None:
    client = build_client()

    response = client.post(
        "/v1/table-discovery-rules", json={"priority": 1, "effect": "include", "x": 1}
    )

    assert response.status_code == 422


def test_update_table_discovery_rule() -> None:
    stub = StubUseCase(UpdateTableDiscoveryRuleUseCaseOutput(**FIELDS))
    client = build_client(update_table_discovery_rule=stub)

    response = client.patch(
        "/v1/table-discovery-rules/r-1", json={"priority": 20, "effect": "exclude"}
    )

    assert response.status_code == 200
    assert stub.requests == [
        UpdateTableDiscoveryRuleUseCaseInput(id="r-1", priority=20, effect="exclude")
    ]


def test_delete_table_discovery_rule_returns_204() -> None:
    stub = StubUseCase(DeleteTableDiscoveryRuleUseCaseOutput())
    client = build_client(delete_table_discovery_rule=stub)

    response = client.delete("/v1/table-discovery-rules/r-1")

    assert response.status_code == 204
    assert stub.requests == [DeleteTableDiscoveryRuleUseCaseInput(id="r-1")]


def test_old_discovery_rules_prefix_is_gone() -> None:
    client = build_client()

    assert client.get("/v1/discovery-rules").status_code == 404
