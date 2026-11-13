"""Define the platform settings router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from context.table_maintenance.adapter.inbound.web.compaction_round.dto import (
    PlatformSettingApiResponse,
    PlatformSettingsApiResponse,
    PlatformSettingsGroupApiResponse,
)
from context.table_maintenance.adapter.inbound.web.shared import (
    WebUseCases,
    use_cases_dependency,
)
from context.table_maintenance.application.port.inbound.compaction_round import (
    GetPlatformSettingsUseCaseInput,
)

platform_settings_router = APIRouter(tags=["platform-settings"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]


@platform_settings_router.get("/platform-settings")
def get_platform_settings(use_cases: UseCases) -> PlatformSettingsApiResponse:
    """Read the platform-level settings the running component was started with, grouped by theme.

    Read-only: the values are set by the platform deployment. Each setting carries a stable
    key, a label, its value and unit, and a one-sentence description.
    """
    output = use_cases.get_platform_settings.execute(GetPlatformSettingsUseCaseInput())
    return PlatformSettingsApiResponse(
        groups=[
            PlatformSettingsGroupApiResponse(
                key=group.key,
                title=group.title,
                items=[
                    PlatformSettingApiResponse(
                        key=item.key,
                        label=item.label,
                        value=item.value,
                        unit=item.unit,
                        description=item.description,
                    )
                    for item in group.items
                ],
            )
            for group in output.groups
        ]
    )
