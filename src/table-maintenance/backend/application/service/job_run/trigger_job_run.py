"""Define the TriggerJobRunService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.job import (
    JobId,
    JobNotActiveError,
    JobNotFoundError,
    MaxActiveRunsExceededError,
)
from application.exceptions import JobDisabledError
from application.exceptions import JobNotFoundError as AppJobNotFoundError
from application.port.inbound import (
    TriggerJobRunUseCaseInput,
    TriggerJobRunUseCase,
)
from application.port.inbound.job_run.trigger_job_run import TriggerJobRunUseCaseOutput

if TYPE_CHECKING:
    from application.service.outbox.event_serializer import EventSerializer
    from application.port.outbound.event_outbox.event_outbox_store import (
        EventOutboxStore,
    )
    from application.port.outbound.job.jobs_repo import JobsRepo
    from application.port.outbound.job_run.job_runs_repo import JobRunsRepo


class TriggerJobRunService(TriggerJobRunUseCase):
    """Triggers a JobRun via Job.trigger() — writes event to outbox for async processing."""

    def __init__(
        self,
        repo: JobsRepo,
        job_runs_repo: JobRunsRepo,
        outbox_repo: EventOutboxStore,
        serializer: EventSerializer,
    ) -> None:
        """Initialize with repos, outbox repo, and serializer."""
        self._repo = repo
        self._job_runs_repo = job_runs_repo
        self._outbox_repo = outbox_repo
        self._serializer = serializer

    def execute(self, request: TriggerJobRunUseCaseInput) -> TriggerJobRunUseCaseOutput:
        """Trigger a new execution of the specified job."""
        try:
            job = self._repo.get(JobId(value=request.job_id))
        except JobNotFoundError as e:
            raise AppJobNotFoundError(e.name) from e

        active_count = self._job_runs_repo.count_active_for_job(job.id)

        try:
            job.trigger(active_run_count=active_count)
        except JobNotActiveError as e:
            raise JobDisabledError(e.job_id) from e
        except MaxActiveRunsExceededError as e:
            raise JobDisabledError(e.job_id) from e

        entries = self._serializer.to_outbox_entries(
            events=job.collect_events(),
            aggregate_type="Job",
            aggregate_id=job.id.value,
        )
        self._outbox_repo.save(entries)

        return TriggerJobRunUseCaseOutput(job_id=job.id.value)
