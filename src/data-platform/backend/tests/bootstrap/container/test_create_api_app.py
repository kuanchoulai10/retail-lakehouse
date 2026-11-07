"""Test that the API app factory serves health and applies every registration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

from bootstrap.container import create_api_app

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import FastAPI


def _registration(path: str, body: str) -> Callable[[FastAPI], None]:
    def register(app: FastAPI) -> None:
        @app.get(path)
        def handler() -> dict[str, str]:
            return {"route": body}

    return register


def test_create_api_app_serves_healthz_and_applies_registrations():
    """The app answers /healthz and every registration's routes."""
    client = TestClient(create_api_app(_registration("/one", "one"), _registration("/two", "two")))

    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert client.get("/one").json() == {"route": "one"}
    assert client.get("/two").json() == {"route": "two"}
