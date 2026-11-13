"""Web adapter for the compaction_round group."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.web.compaction_round.dto import (
    CompactionRoundApiResponse,
    CompactionRoundPartitionApiResponse,
    CompactionRoundPickApiResponse,
    CompactionRoundSkipApiResponse,
    CompactionRoundTableApiResponse,
    PlatformSettingApiResponse,
    PlatformSettingsApiResponse,
    PlatformSettingsGroupApiResponse,
    SchedulerPriorityApiResponse,
    SchedulerSettingsApiResponse,
)
from context.table_maintenance.adapter.inbound.web.compaction_round.router import (
    platform_settings_router,
    router,
)

__all__ = [
    "CompactionRoundApiResponse",
    "CompactionRoundPartitionApiResponse",
    "CompactionRoundPickApiResponse",
    "CompactionRoundSkipApiResponse",
    "CompactionRoundTableApiResponse",
    "PlatformSettingApiResponse",
    "PlatformSettingsApiResponse",
    "PlatformSettingsGroupApiResponse",
    "SchedulerPriorityApiResponse",
    "SchedulerSettingsApiResponse",
    "platform_settings_router",
    "router",
]
