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


def test_requests_without_the_root_path_prefix_still_route():
    """With a root path set, health and registered routes that arrive without the prefix still succeed."""
    client = TestClient(create_api_app(_registration("/v1/one", "one"), root_path="/api"))

    assert client.get("/healthz").status_code == 200
    assert client.get("/v1/one").json() == {"route": "one"}


def test_openapi_servers_point_at_the_root_path():
    """The OpenAPI document names the root path as its server."""
    client = TestClient(create_api_app(root_path="/api"))

    assert client.get("/openapi.json").json()["servers"] == [{"url": "/api"}]


def test_docs_load_the_openapi_document_under_the_root_path():
    """The Swagger UI page fetches the OpenAPI document under the root path."""
    response = TestClient(create_api_app(root_path="/api")).get("/docs")

    assert response.status_code == 200
    assert "'/api/openapi.json'" in response.text


def test_no_root_path_keeps_the_default_docs():
    """Without a root path the OpenAPI document lists no servers and the docs load it from the root."""
    client = TestClient(create_api_app())

    assert "servers" not in client.get("/openapi.json").json()
    assert "'/openapi.json'" in client.get("/docs").text
