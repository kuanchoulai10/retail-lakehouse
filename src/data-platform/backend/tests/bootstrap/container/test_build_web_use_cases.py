"""Test that the web use cases are fully populated and share the application services."""

from __future__ import annotations

from dataclasses import fields
from typing import TYPE_CHECKING, Any

from fastapi.testclient import TestClient

from bootstrap.container import build_repositories, build_use_cases, build_web_use_cases, create_api_app
from context.table_maintenance.adapter.inbound.web import register_routes
from tests.bootstrap.container.container_support import (
    NOW,
    fake_gateways,
    platform_settings,
    sqlite_engine,
)

if TYPE_CHECKING:
    from context.table_maintenance.adapter.inbound.web.shared import WebUseCases

UNKNOWN_RULE = "dr-7zzzzzzzzzzzzzzzzzzzzzzzzz"


def _web_use_cases() -> WebUseCases:
    use_cases = build_use_cases(
        build_repositories(sqlite_engine()), fake_gateways(), platform_settings=platform_settings(), clock=lambda: NOW
    )
    return build_web_use_cases(use_cases)


def test_every_web_use_case_is_populated():
    """All 36 web use case fields are set."""
    web = _web_use_cases()

    assert len(fields(web)) == 36
    assert all(getattr(web, f.name) is not None for f in fields(web))


def test_web_use_cases_reuse_the_application_services():
    """Each web use case is the same object as the application service."""
    use_cases = build_use_cases(
        build_repositories(sqlite_engine()), fake_gateways(), platform_settings=platform_settings(), clock=lambda: NOW
    )

    web = build_web_use_cases(use_cases)

    for f in fields(web):
        assert getattr(web, f.name) is getattr(use_cases, f.name)


def test_app_serves_requests_end_to_end_on_sqlite():
    """The app serves health, save and read requests end to end on SQLite."""
    client = TestClient(create_api_app(lambda app: register_routes(app, _web_use_cases())))

    assert client.get("/healthz").json() == {"status": "ok"}
    saved = client.post("/v1/discovery-policies", json={"name": "sales", **_content(_rule())})
    assert saved.status_code == 201
    fetched = client.get("/v1/discovery-policies/sales").json()
    assert (fetched["version"], [r["outcome"] for r in fetched["rules"]]) == (1, ["manage"])
    stale = client.put("/v1/discovery-policies/sales", json={"version": 0, **_content()})
    assert stale.status_code == 409


def test_saving_a_rule_id_the_policy_does_not_hold_answers_422():
    """A PUT naming a rule id the policy's current version does not hold is refused with 422 and saves nothing."""
    client = TestClient(create_api_app(lambda app: register_routes(app, _web_use_cases())))
    assert client.post("/v1/discovery-policies", json={"name": "sales", **_content()}).status_code == 201

    response = client.put("/v1/discovery-policies/sales", json={"version": 1, **_content(_rule(id=UNKNOWN_RULE))})

    assert response.status_code == 422
    assert f"unknown discovery rule id {UNKNOWN_RULE}" in response.json()["detail"]
    assert client.get("/v1/discovery-policies/sales").json()["version"] == 1


def _rule(**extra: Any) -> dict[str, Any]:  # noqa: ANN401
    return {
        "outcome": "manage",
        "conditions": [{"attribute": "table_name", "operator": "glob", "values": ["orders_*"]}],
        **extra,
    }


def _content(*rules: dict[str, Any]) -> dict[str, Any]:
    return {"description": "", "no_match_outcome": "unmanage", "rules": list(rules)}
