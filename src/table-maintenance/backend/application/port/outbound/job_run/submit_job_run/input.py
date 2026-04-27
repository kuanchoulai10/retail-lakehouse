"""Define the SubmitJobRunInput value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class SubmitJobRunInput(ValueObject):
    """Encapsulates all information needed to submit a job to an external executor.

    Uses only primitive types so that adapter implementations need zero
    domain imports.
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
