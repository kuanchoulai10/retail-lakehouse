"""Define the ForwardTableMaintenanceResultUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class ForwardTableMaintenanceResultUseCaseOutput(UseCaseOutput):
    """Tell whether the result a maintenance job reported was forwarded to the workflow."""

    accepted: bool
