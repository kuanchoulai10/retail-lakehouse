"""Define the SubmitJobRunInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubmitJobRunInput:
    """Input for submitting a job run to an external executor.

    Uses only primitive types so that callers need zero domain imports.
    """

    run_id: str
    job_id: str
    job_type: str
    catalog: str
    table: str
    job_config: dict
    driver_memory: str
    executor_memory: str
    executor_instances: int
    cron_expression: str | None
