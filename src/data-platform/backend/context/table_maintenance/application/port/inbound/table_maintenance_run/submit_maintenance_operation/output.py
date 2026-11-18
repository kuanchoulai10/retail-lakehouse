"""Define the SubmitMaintenanceOperationUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class SubmitMaintenanceOperationUseCaseOutput(UseCaseOutput):
    """Carry the result of the request to submit one attempt of a maintenance operation to Spark."""

    job_name: str
