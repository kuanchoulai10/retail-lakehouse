"""Provide the build_connected_use_cases function."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bootstrap.container.build_catalog_factory import build_catalog_factory
from bootstrap.container.build_engine import build_engine
from bootstrap.container.build_gateways import build_gateways
from bootstrap.container.build_k8s_api import build_k8s_api
from bootstrap.container.build_repositories import build_repositories
from bootstrap.container.build_use_cases import build_use_cases
from bootstrap.container.connect_temporal import connect_temporal
from bootstrap.container.lazy_k8s_api import LazyK8sApi

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from kubernetes.client import CustomObjectsApi
    from temporalio.client import Client

    from bootstrap.configs import AppSettings, TemporalSettings
    from bootstrap.container.use_cases import UseCases
    from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
        AsyncLoopBridge,
    )


def build_connected_use_cases(
    settings: AppSettings,
    bridge: AsyncLoopBridge,
    *,
    connect: Callable[[TemporalSettings], Awaitable[Client]] = connect_temporal,
    k8s_api_factory: Callable[[], CustomObjectsApi] = build_k8s_api,
) -> UseCases:
    """Build every use case on the configured database, Temporal and Kubernetes.

    The gateways' Temporal client is connected on ``bridge``'s loop, since the
    gateways run every call there. The Kubernetes client is built on first use, so
    components that never submit Spark jobs start without a kubeconfig.
    """
    client = bridge.run(lambda: connect(settings.temporal))
    gateways = build_gateways(
        settings,
        client=client,
        bridge=bridge,
        k8s_api=cast("CustomObjectsApi", LazyK8sApi(k8s_api_factory)),
        catalog_factory=build_catalog_factory(settings.catalog),
    )
    return build_use_cases(build_repositories(build_engine(settings)), gateways, catalog_names=settings.catalog.names)
