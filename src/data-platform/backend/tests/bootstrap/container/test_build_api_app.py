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
    """The API builds on SQLite without a kubeconfig and serves health and preset requests."""
    settings = sqlite_settings()
    settings.sqlite.path = str(tmp_path / "tm.db")
    run_migrations(build_engine(settings))
    bridge = AsyncLoopBridge()
    try:
        app = build_api_app(settings, bridge, connect=_connect, k8s_api_factory=_no_kubeconfig)
        client = TestClient(app)

        assert client.get("/healthz").status_code == 200
        presets = client.get("/v1/table-maintenance-presets").json()
    finally:
        bridge.close()

    assert [t["name"] for t in presets] == ["default"]


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
    assert {"/v1/table-maintenance-presets", "/v1/catalogs", "/v1/catalogs/{catalog}"} <= paths
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
        presets = client.get("/v1/table-maintenance-presets").status_code
    finally:
        bridge.close()

    assert servers == [{"url": "/api"}]
    assert presets == 200
