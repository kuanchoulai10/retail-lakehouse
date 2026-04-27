"""Define the SubmitJobRunInMemoryGateway adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.outbound.job_run.submit_job_run.gateway import SubmitJobRunGateway

if TYPE_CHECKING:
    from application.port.outbound.job_run.submit_job_run.input import SubmitJobRunInput


class SubmitJobRunInMemoryGateway(SubmitJobRunGateway):
    """Test double for SubmitJobRunGateway. Records every submitted job."""

    def __init__(self) -> None:
        """Initialize an empty list of submissions."""
        self.submitted: list[SubmitJobRunInput] = []

    def submit(self, submission: SubmitJobRunInput) -> None:
        """Record the submission in memory."""
        self.submitted.append(submission)
