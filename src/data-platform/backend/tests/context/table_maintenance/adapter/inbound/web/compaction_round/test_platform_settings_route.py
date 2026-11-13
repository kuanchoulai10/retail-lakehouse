"""Test the platform settings route."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from context.table_maintenance.application.port.inbound.compaction_round import (
    GetPlatformSettingsUseCaseInput,
    GetPlatformSettingsUseCaseOutput,
    GetPlatformSettingsUseCaseOutputGroup,
    GetPlatformSettingsUseCaseOutputItem,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import StubUseCase, build_client

if TYPE_CHECKING:
    from fastapi import FastAPI

SECRET_WORDS = ("password", "secret", "key", "token", "credential")


def _app() -> FastAPI:
    return cast("FastAPI", build_client().app)


def _output() -> GetPlatformSettingsUseCaseOutput:
    return GetPlatformSettingsUseCaseOutput(
        groups=[
            GetPlatformSettingsUseCaseOutputGroup(
                key="execution_capacity",
                title="Execution capacity",
                items=[
                    GetPlatformSettingsUseCaseOutputItem(
                        key="admission_limit",
                        label="Concurrent operations",
                        value=2,
                        unit="operations",
                        description="How many operations run at once.",
                    ),
                    GetPlatformSettingsUseCaseOutputItem(
                        key="compute_size_s_driver_memory",
                        label="S driver memory",
                        value="768m",
                        unit=None,
                        description="The memory of the driver.",
                    ),
                ],
            )
        ]
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
                        "key": "admission_limit",
                        "label": "Concurrent operations",
                        "value": 2,
                        "unit": "operations",
                        "description": "How many operations run at once.",
                    },
                    {
                        "key": "compute_size_s_driver_memory",
                        "label": "S driver memory",
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


def test_the_scheduler_settings_route_stays():
    """The earlier scheduler settings route is still served beside the platform settings."""
    paths = {getattr(route, "path", None) for route in _app().routes}

    assert {"/v1/scheduler-settings", "/v1/platform-settings"} <= paths


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
