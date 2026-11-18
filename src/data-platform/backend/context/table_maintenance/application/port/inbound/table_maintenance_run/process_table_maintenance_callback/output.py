"""Define the ProcessTableMaintenanceCallbackUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class ProcessTableMaintenanceCallbackUseCaseOutput(UseCaseOutput):
    """Carry the result of the request to forward a Spark job result callback to the workflow."""

    accepted: bool
