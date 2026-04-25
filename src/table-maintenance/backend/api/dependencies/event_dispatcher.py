"""Provide event dispatcher dependencies."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from core.application.domain.model.job.events import JobTriggered
from core.base.event_dispatcher import EventDispatcher
from core.application.event_handler.job_triggered_handler import JobTriggeredHandler

from api.dependencies.repos import get_job_runs_repo

if TYPE_CHECKING:
    from core.application.port.outbound.job_run.job_runs_repo import JobRunsRepo


def get_triggered_handler(
    job_runs_repo: JobRunsRepo = Depends(get_job_runs_repo),
) -> JobTriggeredHandler:
    """Provide the JobTriggeredHandler."""
    return JobTriggeredHandler(job_runs_repo)


def get_event_dispatcher(
    triggered_handler: JobTriggeredHandler = Depends(get_triggered_handler),
) -> EventDispatcher:
    """Provide the EventDispatcher with all registered handlers."""
    dispatcher = EventDispatcher()
    dispatcher.register(JobTriggered, triggered_handler)
    return dispatcher
