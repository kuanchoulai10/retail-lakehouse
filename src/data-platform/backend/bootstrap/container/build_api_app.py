"""Provide the build_api_app function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bootstrap.container.build_connected_use_cases import build_connected_use_cases
from bootstrap.container.build_k8s_api import build_k8s_api
from bootstrap.container.build_web_use_cases import build_web_use_cases
from bootstrap.container.connect_temporal import connect_temporal
from context.table_maintenance.adapter.inbound.web import create_app

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
    """Build the control plane FastAPI app; the Kubernetes client stays lazy."""
    use_cases = build_connected_use_cases(settings, bridge, connect=connect, k8s_api_factory=k8s_api_factory)
    return create_app(build_web_use_cases(use_cases))
