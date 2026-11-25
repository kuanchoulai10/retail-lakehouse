"""Define the CancelTableMaintenanceRunUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class CancelTableMaintenanceRunUseCaseOutput(UseCaseOutput):
    """Carry the run's status after the request and whether the request cancelled it.

    ``cancelled`` is True only when the request cancelled a run pending or waiting to retry; a run in any
    other status was left alone and answers False.
    """

    run_id: str
    status: str
    cancelled: bool
