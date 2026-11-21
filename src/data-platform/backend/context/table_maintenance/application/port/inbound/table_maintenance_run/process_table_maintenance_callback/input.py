"""Define the ProcessTableMaintenanceCallbackUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class ProcessTableMaintenanceCallbackUseCaseInput(UseCaseInput):
    """Carry the request to forward a Spark job result callback to the workflow.

    ``operation`` is None when the callback does not name one; when it does, it must be the run's.
    """

    run_id: str
    attempt: int
    succeeded: bool
    metrics: dict[str, int]
    error: str | None
    operation: str | None = None
