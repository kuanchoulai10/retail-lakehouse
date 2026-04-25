"""Define the JobRunExecutor port interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.application.domain.model.job import Job
    from core.application.domain.model.job_run import JobRun


class JobRunExecutor(ABC):
    """Port for triggering a new execution of a Job.

    Unlike a repository, the executor performs a side-effect in an external
    system (e.g. creating a SparkApplication in Kubernetes). It returns the
    freshly-created JobRun representing that execution.
    """

    @abstractmethod
    def trigger(self, job: Job) -> JobRun:
        """Trigger execution of the given job and return the resulting run."""
        ...
