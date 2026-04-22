"""Compute the next run time from a cron expression."""

from __future__ import annotations

from typing import TYPE_CHECKING

from croniter import CroniterBadCronError, croniter

if TYPE_CHECKING:
    from datetime import datetime


def next_run_from_cron(cron_expr: str, base_time: datetime) -> datetime:
    """Return the next datetime after base_time that matches the cron expression.

    Raises ValueError if the cron expression is invalid.
    """
    try:
        cron = croniter(cron_expr, base_time)
    except (CroniterBadCronError, KeyError) as exc:
        raise ValueError(f"Invalid cron expression: {cron_expr!r}") from exc
    return cron.get_next(type(base_time))
