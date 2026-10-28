"""Define the SubmitMaintenanceOperationUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubmitMaintenanceOperationUseCaseOutput:
    """Carry the result of the request to submit one attempt of a maintenance operation to Spark."""

    job_name: str
