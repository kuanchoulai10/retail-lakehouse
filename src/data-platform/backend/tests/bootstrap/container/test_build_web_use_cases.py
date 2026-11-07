"""Test that the web use cases are fully populated and share the application services."""

from __future__ import annotations

from dataclasses import fields
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

from bootstrap.container import build_repositories, build_use_cases, build_web_use_cases
from context.table_maintenance.adapter.inbound.web import create_app
from tests.bootstrap.container.container_support import (
    NOW,
    fake_gateways,
    sqlite_engine,
)

if TYPE_CHECKING:
    from context.table_maintenance.adapter.inbound.web.shared import WebUseCases


def _web_use_cases() -> WebUseCases:
    use_cases = build_use_cases(build_repositories(sqlite_engine()), fake_gateways(), clock=lambda: NOW)
    return build_web_use_cases(use_cases)


def test_every_web_use_case_is_populated():
    """All 28 web use case fields are set."""
    web = _web_use_cases()

    assert len(fields(web)) == 28
    assert all(getattr(web, f.name) is not None for f in fields(web))


def test_web_use_cases_reuse_the_application_services():
    """Each web use case is the same object as the application service."""
    use_cases = build_use_cases(build_repositories(sqlite_engine()), fake_gateways(), clock=lambda: NOW)

    web = build_web_use_cases(use_cases)

    for f in fields(web):
        assert getattr(web, f.name) is getattr(use_cases, f.name)


def test_app_serves_requests_end_to_end_on_sqlite():
    """The app serves health, create and list requests end to end on SQLite."""
    client = TestClient(create_app(_web_use_cases()))

    assert client.get("/healthz").json() == {"status": "ok"}
    created = client.post("/v1/table-maintenance-presets", json={"name": "nightly"})
    assert created.status_code == 201
    listing = client.get("/v1/table-maintenance-presets")
    assert [item["name"] for item in listing.json()] == ["nightly"]
