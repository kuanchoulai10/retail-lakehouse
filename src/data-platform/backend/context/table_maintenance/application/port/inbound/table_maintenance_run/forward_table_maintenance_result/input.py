"""Define the ForwardTableMaintenanceResultUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class ForwardTableMaintenanceResultUseCaseInput(UseCaseInput):
    """Carry the request to forward the result a maintenance job reports to the workflow.

    ``operation`` is None when the report does not name one; when it does, it must be the run's.
    """

    run_id: str
    attempt: int
    succeeded: bool
    metrics: dict[str, int]
    error: str | None
    operation: str | None = None
