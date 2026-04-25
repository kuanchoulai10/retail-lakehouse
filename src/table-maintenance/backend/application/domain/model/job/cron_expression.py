"""Define the CronExpression value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from croniter import CroniterBadCronError, croniter

from core.base.value_object import ValueObject

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class CronExpression(ValueObject):
    """An immutable, validated cron schedule expression.

    Validates the expression at construction time and provides
    a method to compute the next run time.
    """

    expression: str

    def __post_init__(self) -> None:
        """Validate the cron expression format."""
        try:
            croniter(self.expression)
        except (CroniterBadCronError, KeyError) as exc:
            raise ValueError(f"Invalid cron expression: {self.expression!r}") from exc

    def next_run_after(self, base_time: datetime) -> datetime:
        """Return the next datetime after base_time matching this expression."""
        cron = croniter(self.expression, base_time)
        return cron.get_next(type(base_time))
