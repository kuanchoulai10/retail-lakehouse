from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.domain.model.job_id import JobId
    from application.domain.model.job_run import JobRun
    from application.domain.model.job_run_id import JobRunId


class BaseJobRunsRepo(ABC):
    """Read-only port over JobRun execution instances.

    A JobRun is created by a JobRunExecutor side-effect, not by a repo.create()
    call — this port therefore omits create/delete and only exposes reads.
    """

    @abstractmethod
    def get(self, run_id: JobRunId) -> JobRun: ...

    @abstractmethod
    def list_for_job(self, job_id: JobId) -> list[JobRun]: ...

    @abstractmethod
    def list_all(self) -> list[JobRun]: ...
