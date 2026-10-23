"""Define the ProcessMaintenanceCallbackUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessMaintenanceCallbackUseCaseOutput:
    """Carry the result of the request to forward a Spark job result callback to the workflow."""

    accepted: bool
