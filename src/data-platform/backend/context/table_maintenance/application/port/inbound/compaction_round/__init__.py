"""Inbound ports for the compaction_round group."""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.compaction_round.get_compaction_round import (
    GetCompactionRoundUseCase,
    GetCompactionRoundUseCaseInput,
    GetCompactionRoundUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.compaction_round.get_platform_settings import (
    GetPlatformSettingsUseCase,
    GetPlatformSettingsUseCaseInput,
    GetPlatformSettingsUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.compaction_round.get_scheduler_settings import (
    GetSchedulerSettingsUseCase,
    GetSchedulerSettingsUseCaseInput,
    GetSchedulerSettingsUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.compaction_round.list_compaction_rounds import (
    ListCompactionRoundsUseCase,
    ListCompactionRoundsUseCaseInput,
    ListCompactionRoundsUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.compaction_round.schedule_compaction_round import (
    ScheduleCompactionRoundUseCase,
    ScheduleCompactionRoundUseCaseInput,
    ScheduleCompactionRoundUseCaseOutput,
)

__all__ = [
    "GetCompactionRoundUseCase",
    "GetCompactionRoundUseCaseInput",
    "GetCompactionRoundUseCaseOutput",
    "GetPlatformSettingsUseCase",
    "GetPlatformSettingsUseCaseInput",
    "GetPlatformSettingsUseCaseOutput",
    "GetSchedulerSettingsUseCase",
    "GetSchedulerSettingsUseCaseInput",
    "GetSchedulerSettingsUseCaseOutput",
    "ListCompactionRoundsUseCase",
    "ListCompactionRoundsUseCaseInput",
    "ListCompactionRoundsUseCaseOutput",
    "ScheduleCompactionRoundUseCase",
    "ScheduleCompactionRoundUseCaseInput",
    "ScheduleCompactionRoundUseCaseOutput",
]
