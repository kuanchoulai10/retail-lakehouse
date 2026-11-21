"""Define the SkipTableMaintenanceRunUseCaseInput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseInput


class SkipTableMaintenanceRunUseCaseInput(UseCaseInput):
    """Carry the request to skip a maintenance run that never started.

    ``reason`` says why the run is skipped and ``now`` is when it was skipped.
    """

    run_id: str
    reason: str
    now: datetime
