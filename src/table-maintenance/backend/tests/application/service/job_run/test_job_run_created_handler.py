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
from application.port.outbound.job_run.job_submission import JobSubmission
from application.service.job_run.job_run_created_handler import JobRunCreatedHandler


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


def test_calls_executor_submit():
    """Verify handler calls executor.submit() with a JobSubmission."""
    executor = MagicMock()
    handler = JobRunCreatedHandler(executor)

    handler.handle(_make_event())

    executor.submit.assert_called_once()
    submission = executor.submit.call_args[0][0]
    assert isinstance(submission, JobSubmission)


def test_submission_maps_event_fields():
    """Verify the JobSubmission contains correct values from the event."""
    executor = MagicMock()
    handler = JobRunCreatedHandler(executor)

    handler.handle(_make_event())

    submission = executor.submit.call_args[0][0]
    assert submission.run_id == "r1"
    assert submission.job_id == "j1"
    assert submission.job_type == "expire_snapshots"
    assert submission.catalog == "retail"
    assert submission.table == "orders"
    assert submission.job_config == {"retain_last": 5}
    assert submission.driver_memory == "2g"
    assert submission.executor_memory == "4g"
    assert submission.executor_instances == 2
    assert submission.cron_expression == "0 2 * * *"


def test_submission_with_no_cron():
    """Verify cron_expression is None when event has no cron."""
    executor = MagicMock()
    handler = JobRunCreatedHandler(executor)

    handler.handle(_make_event(cron=None))

    submission = executor.submit.call_args[0][0]
    assert submission.cron_expression is None
