"""Test that the API app builder wires the application and serves requests."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from bootstrap.container import build_api_app, build_engine, run_migrations
from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
    AsyncLoopBridge,
)
from tests.bootstrap.container.container_support import sqlite_settings

if TYPE_CHECKING:
    from kubernetes.client import CustomObjectsApi

    from bootstrap.configs import TemporalSettings


def _no_kubeconfig() -> CustomObjectsApi:
    raise RuntimeError("no kubeconfig")


async def _connect(_: TemporalSettings) -> MagicMock:
    return MagicMock(name="client")


def test_api_builds_and_serves_without_a_kubeconfig(tmp_path):
    """The API builds on SQLite without a kubeconfig and serves health requests and no longer serves presets."""
    settings = sqlite_settings()
    settings.sqlite.path = str(tmp_path / "tm.db")
    run_migrations(build_engine(settings))
    bridge = AsyncLoopBridge()
    try:
        app = build_api_app(settings, bridge, connect=_connect, k8s_api_factory=_no_kubeconfig)
        client = TestClient(app)

        assert client.get("/healthz").status_code == 200
        removed = client.get("/v1/table-maintenance-presets").status_code
    finally:
        bridge.close()

    assert removed == 404


def test_api_mounts_both_contexts(tmp_path):
    """The API serves the table maintenance routes and the catalog routes on one app."""
    settings = sqlite_settings()
    settings.sqlite.path = str(tmp_path / "tm.db")
    run_migrations(build_engine(settings))
    bridge = AsyncLoopBridge()
    try:
        app = build_api_app(settings, bridge, connect=_connect, k8s_api_factory=_no_kubeconfig)
    finally:
        bridge.close()

    paths = {getattr(route, "path", None) for route in app.routes}
    assert {"/v1/discovery-policies", "/v1/catalogs", "/v1/catalogs/{catalog}"} <= paths
    assert app.state.catalog_use_cases is not None
    assert app.state.table_maintenance_use_cases is not None


def test_api_serves_its_docs_under_the_configured_root_path(tmp_path):
    """The configured API root path reaches the app: the OpenAPI server is the prefix, unprefixed routes still serve."""
    settings = sqlite_settings()
    settings.sqlite.path = str(tmp_path / "tm.db")
    settings.api.root_path = "/api"
    run_migrations(build_engine(settings))
    bridge = AsyncLoopBridge()
    try:
        app = build_api_app(settings, bridge, connect=_connect, k8s_api_factory=_no_kubeconfig)
        client = TestClient(app)

        servers = client.get("/openapi.json").json()["servers"]
        status = client.get("/v1/discovery-policies").status_code
    finally:
        bridge.close()

    assert servers == [{"url": "/api"}]
    assert status == 200


def test_api_serves_the_platform_settings_it_was_started_with_and_no_secret(tmp_path):
    """GET /v1/platform-settings reports the running values and nothing of the deployment's secrets."""
    settings = sqlite_settings(
        maintenance_attempt_deadline_seconds=900,
        maintenance_max_attempts=4,
        catalog={"credential": "root:cat4log", "s3_secret_access_key": "SKSECRET"},
        postgres={"db_url": "postgresql+psycopg://tm:s3cr3t-pass@db:5432/tm"},
    )
    settings.sqlite.path = str(tmp_path / "tm.db")
    run_migrations(build_engine(settings))
    bridge = AsyncLoopBridge()
    try:
        app = build_api_app(settings, bridge, connect=_connect, k8s_api_factory=_no_kubeconfig)
        response = TestClient(app).get("/v1/platform-settings")
    finally:
        bridge.close()

    assert response.status_code == 200
    items = {item["key"]: item["value"] for group in response.json()["groups"] for item in group["items"]}
    assert (items["maintenance_attempt_deadline_seconds"], items["maintenance_max_attempts"]) == (900, 4)
    assert not [secret for secret in ("cat4log", "SKSECRET", "s3cr3t-pass") if secret in response.text]
