"""Scheduler-specific configuration."""

from __future__ import annotations

from pydantic import BaseModel


class SchedulerSettings(BaseModel):
    """Settings for the scheduler component."""

    interval_seconds: int = 30
