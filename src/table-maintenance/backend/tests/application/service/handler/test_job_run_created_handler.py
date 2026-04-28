"""Tests for JobRunCreatedHandler."""

from unittest.mock import MagicMock

from application.domain.model.job import (
    CronExpression,
    JobId,
    JobType,
    ResourceConfig,
    TableReference,
)
from application.domain.model.job_run import JobRunId, TriggerType
from application.domain.model.job_run.events import JobRunCreated
from application.port.inbound.job_run.submit_job_run import SubmitJobRunUseCaseInput
from application.service.handler.job_run_created_handler import JobRunCreatedHandler


def _make_event(**overrides) -> JobRunCreated:
    defaults = {
        "run_id": JobRunId(value="r1"),
        "job_id": JobId(value="j1"),
        "trigger_type": TriggerType.SCHEDULED,
        "job_type": JobType.EXPIRE_SNAPSHOTS,
        "table_ref": TableReference(catalog="retail", table="orders"),
        "job_config": {"retain_last": 5},
        "resource_config": ResourceConfig(
            driver_memory="2g", executor_memory="4g", executor_instances=2
        ),
        "cron": CronExpression(expression="0 2 * * *"),
    }
    defaults.update(overrides)
    return JobRunCreated(**defaults)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]


def test_delegates_to_use_case():
    """Verify handler calls use_case.execute() with a SubmitJobRunUseCaseInput."""
    use_case = MagicMock()
    handler = JobRunCreatedHandler(use_case)

    handler.handle(_make_event())

    use_case.execute.assert_called_once()
    inp = use_case.execute.call_args[0][0]
    assert isinstance(inp, SubmitJobRunUseCaseInput)


def test_input_maps_event_fields():
    """Verify the SubmitJobRunUseCaseInput contains correct values from the event."""
    use_case = MagicMock()
    handler = JobRunCreatedHandler(use_case)

    handler.handle(_make_event())

    inp = use_case.execute.call_args[0][0]
    assert inp.run_id == "r1"
    assert inp.job_id == "j1"
    assert inp.job_type == "expire_snapshots"
    assert inp.catalog == "retail"
    assert inp.table == "orders"
    assert inp.job_config == {"retain_last": 5}
    assert inp.driver_memory == "2g"
    assert inp.executor_memory == "4g"
    assert inp.executor_instances == 2
    assert inp.cron_expression == "0 2 * * *"


def test_input_with_no_cron():
    """Verify cron_expression is None when event has no cron."""
    use_case = MagicMock()
    handler = JobRunCreatedHandler(use_case)

    handler.handle(_make_event(cron=None))

    inp = use_case.execute.call_args[0][0]
    assert inp.cron_expression is None
