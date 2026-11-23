"""Define the SubmitMaintenanceOperationUseCaseInput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseInput


class SubmitMaintenanceOperationUseCaseInput(UseCaseInput):
    """Carry the request to submit one attempt of a run's maintenance operation to Spark.

    ``operation`` must be the run's own; the where clauses and the procedure arguments are the run's.
    ``size`` is the compute size the attempt runs at.
    """

    run_id: str
    operation: str
    attempt: int
    result_report_base_url: str
    now: datetime
    size: str
