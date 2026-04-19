"""Tests for job_to_values."""

from datetime import UTC, datetime

from adapter.outbound.job.sql.job_to_values import job_to_values
from application.domain.model.job import Job, JobId, JobType


def _make_job() -> Job:
    """Provide a sample Job entity."""
    return Job(
        id=JobId(value="abc1234567"),
        job_type=JobType.REWRITE_DATA_FILES,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
        catalog="retail",
        table="inventory.orders",
        job_config={"rewrite_all": True},
        cron="0 2 * * *",
        enabled=True,
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
        "enabled",
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
    assert values["enabled"] is True
    assert values["job_config"] == {"rewrite_all": True}
