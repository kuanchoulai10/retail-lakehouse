"""Provide the build_openapi_document function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bootstrap.configs import AppSettings, DatabaseBackend, SqliteSettings
from bootstrap.container.build_api_app import build_api_app
from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
    AsyncLoopBridge,
)

if TYPE_CHECKING:
    from kubernetes.client import CustomObjectsApi
    from temporalio.client import Client

    from bootstrap.configs import TemporalSettings


class _OfflineTemporalClient:
    """Stands in for the Temporal client: building the document never calls Temporal."""

    def __getattr__(self, name: str) -> Any:
        msg = f"the OpenAPI document is built without Temporal (used {name})"
        raise RuntimeError(msg)


async def _offline_temporal(_: TemporalSettings) -> Client:
    return cast("Client", _OfflineTemporalClient())


def _no_kubeconfig() -> CustomObjectsApi:
    raise RuntimeError("the OpenAPI document is built without Kubernetes")


def build_openapi_document() -> dict[str, Any]:
    """Build the real API app on in-memory SQLite and return its OpenAPI document.

    The root path is pinned empty so the document the console is generated from does
    not depend on where the API is deployed.
    """
    settings = AppSettings.model_validate(
        {
            "database_backend": DatabaseBackend.SQLITE,
            "sqlite": SqliteSettings(path=":memory:"),
            "api": {"root_path": ""},
        }
    )
    bridge = AsyncLoopBridge()
    try:
        app = build_api_app(settings, bridge, connect=_offline_temporal, k8s_api_factory=_no_kubeconfig)
        return app.openapi()
    finally:
        bridge.close()
