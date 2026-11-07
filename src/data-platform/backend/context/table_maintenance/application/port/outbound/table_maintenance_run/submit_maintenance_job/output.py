"""Define the SubmitMaintenanceJobGatewayOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubmitMaintenanceJobGatewayOutput:
    """Carry the result of the request to submit a maintenance job."""

    job_name: str
