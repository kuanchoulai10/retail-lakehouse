from __future__ import annotations

import importlib
import inspect
import pkgutil
from dataclasses import fields
from typing import cast
from unittest.mock import MagicMock

from pyiceberg.catalog import Catalog

import context.table_maintenance.application.service
from context.table_maintenance.adapter.outbound.table.pyiceberg import (
    ReadTableMetadataPyIcebergGateway,
)
from context.table_maintenance.adapter.hybrid.temporal.outbound.table_discovery_settings import (
    UpdateTableDiscoveryScheduleTemporalGateway,
)
from context.table_maintenance.adapter.outbound.table_maintenance_preset.sql import (
    TableMaintenancePresetsSqlRepo,
)
from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s import (
    DeleteMaintenanceJobK8sGateway,
    ReadMaintenanceJobK8sGateway,
    SubmitMaintenanceJobK8sGateway,
)
from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
    AsyncLoopBridge,
)
from context.table_maintenance.adapter.hybrid.temporal.outbound.table import (
    SendDiscoveryRequestTemporalGateway,
    SendTableChangeTemporalGateway,
)
from context.table_maintenance.adapter.hybrid.temporal.outbound.table_maintenance_run import (
    SendMaintenanceResultTemporalGateway,
)
from context.table_maintenance.application.port.inbound.table_maintenance_preset import (
    ListTableMaintenancePresetsUseCaseInput,
)
from base import UseCase
from bootstrap.container import (
    build_gateways,
    build_repositories,
    build_use_cases,
)
from tests.bootstrap.container.container_support import (
    NOW,
    fake_gateways,
    sqlite_engine,
    sqlite_settings,
)


def _all_service_classes() -> set[type]:
    found: set[type] = set()
    for module_info in pkgutil.walk_packages(
        context.table_maintenance.application.service.__path__,
        prefix="context.table_maintenance.application.service.",
    ):
        module = importlib.import_module(module_info.name)
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ == module.__name__ and obj.__name__.endswith("Service") and issubclass(obj, UseCase):
                found.add(obj)
    return found


def test_repositories_are_sql_repos_on_the_engine():
    repos = build_repositories(sqlite_engine())

    assert isinstance(repos.table_maintenance_presets, TableMaintenancePresetsSqlRepo)
    assert all(getattr(repos, f.name) is not None for f in fields(repos))


def test_gateways_are_built_without_connecting():
    bridge = AsyncLoopBridge()
    try:
        client = MagicMock(name="temporal-client")
        k8s_api = MagicMock(name="custom-objects-api")
        loaded: list[str] = []

        def catalog_factory(name: str) -> Catalog:
            loaded.append(name)
            return cast("Catalog", object())

        gateways = build_gateways(
            sqlite_settings(),
            client=client,
            bridge=bridge,
            k8s_api=k8s_api,
            catalog_factory=catalog_factory,
        )
    finally:
        bridge.close()

    assert isinstance(gateways.read_table_metadata, ReadTableMetadataPyIcebergGateway)
    assert isinstance(gateways.send_table_change, SendTableChangeTemporalGateway)
    assert isinstance(gateways.send_discovery_request, SendDiscoveryRequestTemporalGateway)
    assert isinstance(gateways.send_maintenance_result, SendMaintenanceResultTemporalGateway)
    assert isinstance(
        gateways.update_table_discovery_schedule,
        UpdateTableDiscoveryScheduleTemporalGateway,
    )
    assert isinstance(gateways.submit_maintenance_job, SubmitMaintenanceJobK8sGateway)
    assert isinstance(gateways.read_maintenance_job, ReadMaintenanceJobK8sGateway)
    assert isinstance(gateways.delete_maintenance_job, DeleteMaintenanceJobK8sGateway)
    assert loaded == []
    assert client.mock_calls == []
    assert k8s_api.mock_calls == []


def test_use_cases_hold_one_instance_of_every_service():
    use_cases = build_use_cases(build_repositories(sqlite_engine()), fake_gateways(), clock=lambda: NOW)

    values = [getattr(use_cases, f.name) for f in fields(use_cases)]
    assert all(isinstance(value, UseCase) for value in values)
    assert {type(value) for value in values} == _all_service_classes()
    assert len(values) == len(_all_service_classes())


def test_use_cases_work_against_the_sql_repos():
    use_cases = build_use_cases(build_repositories(sqlite_engine()), fake_gateways(), clock=lambda: NOW)

    listing = use_cases.list_table_maintenance_presets.execute(ListTableMaintenancePresetsUseCaseInput())

    assert listing.items == []
