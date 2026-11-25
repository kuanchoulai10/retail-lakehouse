"""Test that the use case container wires repositories, gateways and every service."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from dataclasses import fields
from datetime import timedelta
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock

import pytest

import context.table_maintenance.application.service
from base import UseCase
from bootstrap.container import (
    build_gateways,
    build_platform_settings,
    build_repositories,
    build_use_cases,
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
from context.table_maintenance.adapter.outbound.table.prometheus import ReadTableMetricHistoryPrometheusGateway
from context.table_maintenance.adapter.outbound.table.pyiceberg import (
    ReadTableMetadataPyIcebergGateway,
)
from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s import (
    DeleteMaintenanceJobK8sGateway,
    ReadMaintenanceJobEvidenceK8sGateway,
    ReadMaintenanceJobK8sGateway,
    ReadMaintenanceJobProcessesK8sGateway,
    SubmitMaintenanceJobK8sGateway,
)
from context.table_maintenance.adapter.outbound.table_maintenance_run.s3 import (
    ReadMaintenanceEventLogS3Gateway,
)
from context.table_maintenance.application.domain.model.table import (
    DEFAULT_PARTITION_SELECTION_SETTINGS,
    OperationCooldowns,
    PartitionSelectionSettings,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    ListTableDiscoveryPoliciesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run import GetPlatformSettingsUseCaseInput
from context.table_maintenance.application.service.table import PlanTableMaintenanceService
from context.table_maintenance.application.service.table_discovery_policy import (
    EnsureDefaultTableDiscoveryPolicyService,
)
from context.table_maintenance.application.service.table_maintenance_policy import (
    EnsureDefaultTableMaintenancePolicyService,
)
from tests.bootstrap.container.container_support import (
    NOW,
    fake_gateways,
    platform_settings,
    sqlite_engine,
    sqlite_settings,
)

if TYPE_CHECKING:
    from pyiceberg.catalog import Catalog


MIGRATION_ONLY_SERVICES: set[type] = {
    EnsureDefaultTableMaintenancePolicyService,
    EnsureDefaultTableDiscoveryPolicyService,
}
"""Services the migrate component builds itself (`run_migrations`); no API, worker or consumer calls them."""


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
    """Every repository is a SQL repository bound to the engine."""
    repos = build_repositories(sqlite_engine())

    assert all(getattr(repos, f.name) is not None for f in fields(repos))


def test_gateways_are_built_without_connecting():
    """The gateways are built without opening a connection."""
    bridge = AsyncLoopBridge()
    try:
        client = MagicMock(name="temporal-client")
        k8s_api = MagicMock(name="custom-objects-api")
        core_api = MagicMock(name="core-v1-api")
        loaded: list[str] = []

        def catalog_factory(name: str) -> Catalog:
            loaded.append(name)
            return cast("Catalog", object())

        gateways = build_gateways(
            sqlite_settings(),
            client=client,
            bridge=bridge,
            k8s_api=k8s_api,
            k8s_core_api=core_api,
            catalog_factory=catalog_factory,
        )
    finally:
        bridge.close()

    assert isinstance(gateways.read_table_metadata, ReadTableMetadataPyIcebergGateway)
    assert isinstance(gateways.send_table_change, SendTableChangeTemporalGateway)
    assert isinstance(gateways.send_discovery_request, SendDiscoveryRequestTemporalGateway)
    assert isinstance(gateways.send_maintenance_result, SendMaintenanceResultTemporalGateway)
    assert isinstance(gateways.submit_maintenance_job, SubmitMaintenanceJobK8sGateway)
    assert isinstance(gateways.read_maintenance_job, ReadMaintenanceJobK8sGateway)
    assert isinstance(gateways.delete_maintenance_job, DeleteMaintenanceJobK8sGateway)
    assert isinstance(gateways.read_maintenance_job_processes, ReadMaintenanceJobProcessesK8sGateway)
    assert isinstance(gateways.read_maintenance_job_evidence, ReadMaintenanceJobEvidenceK8sGateway)
    assert isinstance(gateways.read_maintenance_event_log, ReadMaintenanceEventLogS3Gateway)
    assert isinstance(gateways.read_table_metric_history, ReadTableMetricHistoryPrometheusGateway)
    assert loaded == []
    assert client.mock_calls == []
    assert k8s_api.mock_calls == []
    assert core_api.mock_calls == []


def test_use_cases_hold_one_instance_of_every_service():
    """The use cases hold exactly one instance of every application service the migrate component does not own."""
    use_cases = build_use_cases(
        build_repositories(sqlite_engine()), fake_gateways(), platform_settings=platform_settings(), clock=lambda: NOW
    )

    values = [getattr(use_cases, f.name) for f in fields(use_cases)]
    assert all(isinstance(value, UseCase) for value in values)
    expected = _all_service_classes() - MIGRATION_ONLY_SERVICES
    assert {type(value) for value in values} == expected
    assert len(values) == len(expected)


def test_use_cases_work_against_the_sql_repos():
    """A built use case runs against the SQL repositories."""
    use_cases = build_use_cases(
        build_repositories(sqlite_engine()), fake_gateways(), platform_settings=platform_settings(), clock=lambda: NOW
    )

    policies = use_cases.list_table_discovery_policies.execute(ListTableDiscoveryPoliciesUseCaseInput())

    assert policies.items == ()


def test_the_platform_settings_report_the_values_they_are_given():
    """The platform settings use case lists the settings the composition root hands it."""
    use_cases = build_use_cases(
        build_repositories(sqlite_engine()),
        fake_gateways(),
        clock=lambda: NOW,
        platform_settings=build_platform_settings(
            sqlite_settings(maintenance={"attempt_deadline_seconds": 900, "max_attempts": 6})
        ),
    )

    output = use_cases.get_platform_settings.execute(GetPlatformSettingsUseCaseInput())

    values = {item.key: item.value for group in output.groups for item in group.items}
    assert (values["maintenance_attempt_deadline_seconds"], values["maintenance_max_attempts"]) == (900, 6)


def test_the_planner_is_given_the_cooldowns():
    """The planner reads the cooldowns build_use_cases is given, the platform default otherwise."""
    cooldowns = OperationCooldowns.platform_default().with_changes(rewrite_data_files=timedelta(minutes=5))
    built = build_use_cases(
        build_repositories(sqlite_engine()),
        fake_gateways(),
        clock=lambda: NOW,
        platform_settings=platform_settings(),
        cooldowns=cooldowns,
    )
    default = build_use_cases(
        build_repositories(sqlite_engine()), fake_gateways(), clock=lambda: NOW, platform_settings=platform_settings()
    )

    for use_cases, expected in ((built, cooldowns), (default, OperationCooldowns.platform_default())):
        planner = use_cases.plan_table_maintenance
        assert isinstance(planner, PlanTableMaintenanceService)
        assert planner._cooldowns == expected  # noqa: SLF001


def test_the_planner_is_given_the_partition_selection():
    """The planner reads the partition selection build_use_cases is given, the platform default otherwise."""
    selection = PartitionSelectionSettings(
        partitions_per_job=4, quiet_period=timedelta(0), max_quiet_wait=timedelta(seconds=600)
    )
    built = build_use_cases(
        build_repositories(sqlite_engine()),
        fake_gateways(),
        clock=lambda: NOW,
        platform_settings=platform_settings(),
        partition_selection=selection,
    )
    default = build_use_cases(
        build_repositories(sqlite_engine()), fake_gateways(), clock=lambda: NOW, platform_settings=platform_settings()
    )

    for use_cases, expected in ((built, selection), (default, DEFAULT_PARTITION_SELECTION_SETTINGS)):
        planner = use_cases.plan_table_maintenance
        assert isinstance(planner, PlanTableMaintenanceService)
        assert planner._partition_selection == expected  # noqa: SLF001


def test_the_platform_settings_are_required():
    """No caller can build the use cases without saying which values the platform settings show."""
    build = cast("Any", build_use_cases)
    with pytest.raises(TypeError, match="platform_settings"):
        build(build_repositories(sqlite_engine()), fake_gateways(), clock=lambda: NOW)
