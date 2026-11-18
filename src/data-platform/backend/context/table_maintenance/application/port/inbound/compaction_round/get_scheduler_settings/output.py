"""Define the GetSchedulerSettingsUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class GetSchedulerSettingsUseCaseOutput(UseCaseOutput):
    """Carry how often a round runs, its GB·hour budget, how long a grant lasts and each priority, P0 first."""

    class Priority(UseCaseOutput):
        """One priority: the weight its candidates' scores are multiplied by, and how long they may wait."""

        priority: str
        weight: float
        sla_seconds: int

    round_seconds: int
    budget_gb_hours: float
    grant_lease_seconds: int
    priorities: tuple[Priority, ...]
