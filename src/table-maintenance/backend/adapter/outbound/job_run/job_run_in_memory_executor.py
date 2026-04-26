"""Define the JobRunInMemoryExecutor adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.outbound.job_run.job_run_executor import JobRunExecutor

if TYPE_CHECKING:
    from application.port.outbound.job_run.job_submission import JobSubmission


class JobRunInMemoryExecutor(JobRunExecutor):
    """Test double for JobRunExecutor. Records every submitted job."""

    def __init__(self) -> None:
        """Initialize an empty list of submissions."""
        self.submitted: list[JobSubmission] = []

    def submit(self, submission: JobSubmission) -> None:
        """Record the submission in memory."""
        self.submitted.append(submission)
