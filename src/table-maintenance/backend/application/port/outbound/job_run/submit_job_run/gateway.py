"""Define the SubmitJobRunGateway port interface."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base.gateway import Gateway

if TYPE_CHECKING:
    from application.port.outbound.job_run.submit_job_run.input import SubmitJobRunInput


class SubmitJobRunGateway(Gateway):
    """Gateway for submitting a job to an external execution system.

    The gateway performs a side-effect (e.g. creating a SparkApplication
    in Kubernetes). It does not create domain entities — that responsibility
    belongs to the application service layer.
    """

    @abstractmethod
    def submit(self, submission: SubmitJobRunInput) -> None:
        """Submit the job for execution in the external system."""
        ...
