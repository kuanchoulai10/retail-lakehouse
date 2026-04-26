"""Tests for job_to_values."""

from datetime import UTC, datetime

from core.adapter.outbound.job.sql.job_to_values import job_to_values
from application.domain.model.job import (
    CronExpression,
    Job,
    JobId,
    JobStatus,
    JobType,
    TableReference,
)


def _make_job() -> Job:
    """Provide a sample Job entity."""
    return Job(
        id=JobId(value="abc1234567"),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
        table_ref=TableReference(catalog="retail", table="inventory.orders"),
        job_config={"rewrite_all": True},
        cron=CronExpression(expression="0 2 * * *"),
        status=JobStatus.ACTIVE,
    )


def test_values_has_all_columns():
    """Verify that the output dict contains all expected column keys."""
    values = job_to_values(_make_job())
    assert set(values.keys()) == {
        "id",
        "job_type",
        "catalog",
        "table",
        "job_config",
        "cron",
        "status",
        "next_run_at",
        "max_active_runs",
        "created_at",
        "updated_at",
    }


def test_enum_fields_serialized_as_strings():
    """Verify that enum fields are serialized as plain strings."""
    values = job_to_values(_make_job())
    assert values["job_type"] == "rewrite_data_files"


def test_scalars_passthrough():
    """Verify that scalar fields pass through unchanged."""
    values = job_to_values(_make_job())
    assert values["id"] == "abc1234567"
    assert values["catalog"] == "retail"
    assert values["table"] == "inventory.orders"
    assert values["cron"] == "0 2 * * *"
    assert values["status"] == "active"
    assert values["job_config"] == {"rewrite_all": True}
