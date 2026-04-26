"""Define the JobRunExecutor port interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.port.outbound.job_run.job_submission import JobSubmission


class JobRunExecutor(ABC):
    """Port for submitting a job to an external execution system.

    The executor performs a side-effect (e.g. creating a SparkApplication
    in Kubernetes). It does not create domain entities — that responsibility
    belongs to the application service layer.
    """

    @abstractmethod
    def submit(self, submission: JobSubmission) -> None:
        """Submit the job for execution in the external system."""
        ...
