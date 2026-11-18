"""Test the discovery rules routes: read, replace whole, covered catalogs."""

from __future__ import annotations

from typing import Any

import pytest

from context.table_maintenance.application.exceptions import ConflictError, ValidationError
from context.table_maintenance.application.port.inbound.table_discovery_rules import (
    GetTableDiscoveryRulesUseCaseOutput,
    ListCoveredCatalogsUseCaseOutput,
    ReplaceTableDiscoveryRulesUseCaseInput,
    ReplaceTableDiscoveryRulesUseCaseOutput,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import (
    NOW,
    StubUseCase,
    build_client,
)

FIELDS: dict[str, Any] = {
    "id": "r-1",
    "priority": 10,
    "action": "exclude",
    "enabled": True,
    "catalogs": ("*",),
    "namespaces": ("production_*",),
    "tables": ("tmp_*", "staging_*"),
    "created_at": NOW,
    "updated_at": NOW,
}
BODY_RULE: dict[str, Any] = {
    "priority": 10,
    "action": "exclude",
    "enabled": True,
    "catalogs": ["*"],
    "namespaces": ["production_*"],
    "tables": ["tmp_*", "staging_*"],
}
SECOND_RULE: dict[str, Any] = {**BODY_RULE, "priority": 20}
RULE_FIELDS: dict[str, Any] = {
    **BODY_RULE,
    "catalogs": ("*",),
    "namespaces": ("production_*",),
    "tables": ("tmp_*", "staging_*"),
}
SECOND_RULE_FIELDS: dict[str, Any] = {**RULE_FIELDS, "priority": 20}


def test_get_discovery_rules_returns_version_and_rules() -> None:
    """GET answers the list's version and its rules."""
    output = GetTableDiscoveryRulesUseCaseOutput(
        version=3, rules=(GetTableDiscoveryRulesUseCaseOutput.TableDiscoveryRule(**FIELDS),)
    )
    response = build_client(get_table_discovery_rules=StubUseCase(output)).get("/v1/discovery-rules")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 3
    assert body["rules"][0]["id"] == "r-1"
    assert body["rules"][0]["tables"] == ["tmp_*", "staging_*"]


def test_put_discovery_rules_passes_the_whole_list_and_returns_it() -> None:
    """PUT hands the whole list and its version to the use case and answers the saved list."""
    stub = StubUseCase(
        ReplaceTableDiscoveryRulesUseCaseOutput(
            version=4, rules=(ReplaceTableDiscoveryRulesUseCaseOutput.TableDiscoveryRule(**FIELDS),)
        )
    )
    response = build_client(replace_table_discovery_rules=stub).put(
        "/v1/discovery-rules",
        json={"version": 3, "rules": [{"id": "r-1", **BODY_RULE}, SECOND_RULE]},
    )
    assert response.status_code == 200
    assert response.json()["version"] == 4
    assert stub.requests == [
        ReplaceTableDiscoveryRulesUseCaseInput(
            version=3,
            rules=(
                ReplaceTableDiscoveryRulesUseCaseInput.TableDiscoveryRule(id="r-1", **RULE_FIELDS),
                ReplaceTableDiscoveryRulesUseCaseInput.TableDiscoveryRule(id=None, **SECOND_RULE_FIELDS),
            ),
        )
    ]


@pytest.mark.parametrize(
    ("error", "status"), [(ValidationError("priority 10 twice"), 422), (ConflictError("stale"), 409)]
)
def test_put_discovery_rules_maps_errors(error: Exception, status: int) -> None:
    """Equal priorities answer 422 and a stale version 409."""
    client = build_client(replace_table_discovery_rules=StubUseCase(error=error))
    response = client.put("/v1/discovery-rules", json={"version": 0, "rules": []})
    assert (response.status_code, response.json()) == (status, {"detail": str(error)})


def test_put_discovery_rules_rejects_unknown_key() -> None:
    """A rule with an unknown key is rejected with 422."""
    response = build_client().put("/v1/discovery-rules", json={"version": 0, "rules": [{**BODY_RULE, "effect": "x"}]})
    assert response.status_code == 422


def test_list_covered_catalogs() -> None:
    """GET /catalogs answers the catalogs maintenance covers."""
    stub = StubUseCase(ListCoveredCatalogsUseCaseOutput(catalogs=("iceberg",)))
    response = build_client(list_covered_catalogs=stub).get("/v1/discovery-rules/catalogs")
    assert (response.status_code, response.json()) == (200, {"catalogs": ["iceberg"]})


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/v1/table-discovery-rules"),
        ("POST", "/v1/table-discovery-rules"),
        ("PATCH", "/v1/table-discovery-rules/r-1"),
        ("DELETE", "/v1/table-discovery-rules/r-1"),
        ("GET", "/v1/table-discovery-settings"),
        ("PUT", "/v1/table-discovery-settings"),
        ("GET", "/v1/table-discovery-settings/catalogs"),
        ("POST", "/v1/table-discovery-settings/scan"),
        ("POST", "/v1/discovery-rules/preview"),
    ],
)
def test_old_discovery_endpoints_are_gone(method: str, path: str) -> None:
    """The per-rule, switch, scan, old covered-catalog and preview endpoints no longer exist."""
    response = build_client().request(method, path, json={})
    assert response.status_code == 404
