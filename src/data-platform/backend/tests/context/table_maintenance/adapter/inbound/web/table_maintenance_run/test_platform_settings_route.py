"""Test the platform settings route."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    PlatformComputeSize,
    PlatformSettings,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    GetPlatformSettingsUseCaseInput,
    GetPlatformSettingsUseCaseOutput,
)
from context.table_maintenance.application.service.table_maintenance_run import GetPlatformSettingsService
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import StubUseCase, build_client

if TYPE_CHECKING:
    from fastapi import FastAPI

SECRET_WORDS = ("password", "secret", "key", "token", "credential")


def _app() -> FastAPI:
    return cast("FastAPI", build_client().app)


def _output() -> GetPlatformSettingsUseCaseOutput:
    return GetPlatformSettingsUseCaseOutput(
        groups=(
            GetPlatformSettingsUseCaseOutput.Group(
                key="execution_capacity",
                title="Execution capacity",
                items=(
                    GetPlatformSettingsUseCaseOutput.Setting(
                        key="maintenance_max_attempts",
                        label="Attempts per operation",
                        value=3,
                        unit="attempts",
                        description="How many times an operation is tried.",
                    ),
                    GetPlatformSettingsUseCaseOutput.Setting(
                        key="compute_size_s_coordinator_memory",
                        label="S coordinator memory",
                        value="768m",
                        unit=None,
                        description="The memory of the driver.",
                    ),
                ),
            ),
        )
    )


def test_serves_the_platform_settings_grouped():
    """The route answers each group with key and title, and each item with key, label, value, unit and description."""
    stub = StubUseCase(_output())

    response = build_client(get_platform_settings=stub).get("/v1/platform-settings")

    assert response.status_code == 200
    assert response.json() == {
        "groups": [
            {
                "key": "execution_capacity",
                "title": "Execution capacity",
                "items": [
                    {
                        "key": "maintenance_max_attempts",
                        "label": "Attempts per operation",
                        "value": 3,
                        "unit": "attempts",
                        "description": "How many times an operation is tried.",
                    },
                    {
                        "key": "compute_size_s_coordinator_memory",
                        "label": "S coordinator memory",
                        "value": "768m",
                        "unit": None,
                        "description": "The memory of the driver.",
                    },
                ],
            }
        ]
    }
    assert stub.requests == [GetPlatformSettingsUseCaseInput()]


def test_the_route_is_read_only():
    """Only GET is offered on the platform settings path."""
    client = build_client(get_platform_settings=StubUseCase(_output()))

    assert [client.post("/v1/platform-settings").status_code, client.put("/v1/platform-settings").status_code] == [
        405,
        405,
    ]
    assert client.delete("/v1/platform-settings").status_code == 405
    assert client.patch("/v1/platform-settings").status_code == 405


def test_the_response_schema_has_no_secret_looking_field():
    """No property of the response schema is named like a secret; ``key`` is a setting's stable identifier."""
    schema = _app().openapi()
    names = [
        name
        for model, definition in schema["components"]["schemas"].items()
        if "PlatformSetting" in model
        for name in [model, *definition.get("properties", {})]
        if name != "key"
    ]

    assert names
    assert not [name for name in names if any(word in name.lower() for word in SECRET_WORDS)]


def test_the_route_has_its_own_openapi_tag():
    """The route is tagged platform-settings alone, so the generated client files it apart from the runs."""
    operation = _app().openapi()["paths"]["/v1/platform-settings"]["get"]

    assert operation["tags"] == ["platform-settings"]


def test_platform_settings_route_lists_partition_selection():
    """The five groups the service builds reach the client, the compaction partition selection before discovery."""
    settings = PlatformSettings(
        attempt_deadline_seconds=21600,
        max_attempts=3,
        queue_wait_limit_seconds=86400,
        compute_sizes=(
            PlatformComputeSize(size=ComputeSize.S, coordinator_memory="768m", worker_memory="768m", worker_count=1),
        ),
        rewrite_data_files_cooldown_seconds=3600,
        rewrite_manifests_cooldown_seconds=21600,
        expire_snapshots_cooldown_seconds=21600,
        remove_orphan_files_interval_seconds=604800,
        failure_backoff_cap_seconds=86400,
        discovery_interval_seconds=600,
        compaction_partitions_per_job=10,
        compaction_quiet_seconds=120,
        compaction_max_quiet_wait_seconds=3600,
    )

    response = build_client(get_platform_settings=GetPlatformSettingsService(settings)).get("/v1/platform-settings")

    groups = response.json()["groups"]
    assert [g["key"] for g in groups] == [
        "execution_capacity",
        "compute_sizes",
        "cooldown_and_backoff",
        "partition_selection",
        "discovery",
    ]
    assert [(i["key"], i["value"], i["unit"]) for i in groups[3]["items"]] == [
        ("maintenance_compaction_partitions_per_job", 10, "partitions"),
        ("maintenance_compaction_quiet_seconds", 120, "seconds"),
        ("maintenance_compaction_max_quiet_wait_seconds", 3600, "seconds"),
    ]
