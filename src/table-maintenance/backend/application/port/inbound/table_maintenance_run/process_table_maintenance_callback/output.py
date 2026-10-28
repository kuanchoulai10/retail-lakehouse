"""Define the ProcessTableMaintenanceCallbackUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessTableMaintenanceCallbackUseCaseOutput:
    """Carry the result of the request to forward a Spark job result callback to the workflow."""

    accepted: bool
