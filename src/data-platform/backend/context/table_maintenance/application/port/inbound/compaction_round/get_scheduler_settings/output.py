"""Define the GetSchedulerSettingsUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetSchedulerSettingsUseCaseOutputPriority:
    """One priority: the weight its candidates' scores are multiplied by, and how long they may wait."""

    priority: str
    weight: float
    sla_seconds: int


@dataclass(frozen=True)
class GetSchedulerSettingsUseCaseOutput:
    """Carry how often a round runs, its GB·hour budget, how long a grant lasts and each priority, P0 first."""

    round_seconds: int
    budget_gb_hours: float
    grant_lease_seconds: int
    priorities: list[GetSchedulerSettingsUseCaseOutputPriority]
