from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from kubernetes.client import CustomObjectsApi

from adapter.outbound.temporal.async_loop_bridge import AsyncLoopBridge
from bootstrap.configs import TemporalSettings
from bootstrap.container import build_api_app, build_engine, run_migrations
from tests.bootstrap.container.container_support import sqlite_settings


def _no_kubeconfig() -> CustomObjectsApi:
    raise RuntimeError("no kubeconfig")


async def _connect(_: TemporalSettings) -> MagicMock:
    return MagicMock(name="client")


def test_api_builds_and_serves_without_a_kubeconfig(tmp_path):
    settings = sqlite_settings()
    settings.sqlite.path = str(tmp_path / "tm.db")
    run_migrations(build_engine(settings))
    bridge = AsyncLoopBridge()
    try:
        app = build_api_app(
            settings, bridge, connect=_connect, k8s_api_factory=_no_kubeconfig
        )
        client = TestClient(app)

        assert client.get("/healthz").status_code == 200
        templates = client.get("/v1/policy-templates").json()
    finally:
        bridge.close()

    assert [t["name"] for t in templates] == ["default"]
