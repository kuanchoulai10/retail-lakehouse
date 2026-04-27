"""Define the SubmitJobRunInMemoryGateway adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.outbound.job_run.submit_job_run_gateway import SubmitJobRunGateway

if TYPE_CHECKING:
    from application.port.outbound.job_run.job_submission import JobSubmission


class SubmitJobRunInMemoryGateway(SubmitJobRunGateway):
    """Test double for SubmitJobRunGateway. Records every submitted job."""

    def __init__(self) -> None:
        """Initialize an empty list of submissions."""
        self.submitted: list[JobSubmission] = []

    def submit(self, submission: JobSubmission) -> None:
        """Record the submission in memory."""
        self.submitted.append(submission)
