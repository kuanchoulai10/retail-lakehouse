"""Define the DeleteMaintenanceJobGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteMaintenanceJobGatewayInput:
    """Carry the arguments to delete a maintenance job."""

    app_name: str
