"""Define the ScheduleCompactionRoundUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class ScheduleCompactionRoundUseCaseOutput(UseCaseOutput):
    """Say what one compaction round granted: the tables to tell, in pick order, and the budget it used."""

    round_id: str
    granted_table_uuids: tuple[str, ...]
    picked: int
    skipped_total: int
    used_gb_hours: float
    budget_gb_hours: float
