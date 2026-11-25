"""Define the CancelTableMaintenanceRunUseCaseInput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseInput


class CancelTableMaintenanceRunUseCaseInput(UseCaseInput):
    """Carry the request to cancel a maintenance run with no attempt in flight.

    ``now`` is when the run was cancelled.
    """

    run_id: str
    now: datetime
