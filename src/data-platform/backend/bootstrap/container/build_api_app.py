"""Provide the build_api_app function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bootstrap.container.build_catalog_web_use_cases import build_catalog_web_use_cases
from bootstrap.container.build_connected_use_cases import build_connected_use_cases
from bootstrap.container.build_k8s_api import build_k8s_api
from bootstrap.container.build_polaris_http_client import build_polaris_http_client
from bootstrap.container.build_web_use_cases import build_web_use_cases
from bootstrap.container.connect_temporal import connect_temporal
from bootstrap.container.create_api_app import create_api_app
from context.catalog.adapter.inbound.web import register_routes as register_catalog_routes
from context.table_maintenance.adapter.inbound.web import register_routes

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from fastapi import FastAPI
    from kubernetes.client import CustomObjectsApi
    from temporalio.client import Client

    from bootstrap.configs import AppSettings, TemporalSettings
    from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
        AsyncLoopBridge,
    )


def build_api_app(
    settings: AppSettings,
    bridge: AsyncLoopBridge,
    *,
    connect: Callable[[TemporalSettings], Awaitable[Client]] = connect_temporal,
    k8s_api_factory: Callable[[], CustomObjectsApi] = build_k8s_api,
) -> FastAPI:
    """Build the API app with both contexts; the Kubernetes client and the Polaris token stay lazy."""
    use_cases = build_connected_use_cases(settings, bridge, connect=connect, k8s_api_factory=k8s_api_factory)
    polaris = build_polaris_http_client(settings.catalog)
    return create_api_app(
        lambda app: register_routes(app, build_web_use_cases(use_cases)),
        lambda app: register_catalog_routes(app, build_catalog_web_use_cases(polaris)),
    )
