"""Tests for row_to_job."""

from datetime import UTC, datetime

from adapter.outbound.job.sql.row_to_job import row_to_job
from core.application.domain.model.job import (
    CronExpression,
    JobId,
    JobStatus,
    JobType,
    TableReference,
)


def test_row_maps_to_job():
    """Verify that a row dict is correctly mapped to a Job entity."""
    row = {
        "id": "abc1234567",
        "job_type": "rewrite_data_files",
        "catalog": "retail",
        "table": "inventory.orders",
        "job_config": {"rewrite_all": True},
        "cron": None,
        "status": "active",
        "next_run_at": None,
        "max_active_runs": 1,
        "created_at": datetime(2026, 4, 10, tzinfo=UTC),
        "updated_at": datetime(2026, 4, 10, tzinfo=UTC),
    }

    job = row_to_job(row)

    assert job.id == JobId(value="abc1234567")
    assert job.job_type == JobType.REWRITE_DATA_FILES
    assert job.table_ref == TableReference(catalog="retail", table="inventory.orders")
    assert job.job_config == {"rewrite_all": True}
    assert job.cron is None
    assert job.status == JobStatus.ACTIVE
    assert job.next_run_at is None
    assert job.max_active_runs == 1
    assert job.created_at == datetime(2026, 4, 10, tzinfo=UTC)
    assert job.updated_at == datetime(2026, 4, 10, tzinfo=UTC)


def test_row_preserves_cron():
    """Verify that a non-null cron value is preserved during mapping."""
    row = {
        "id": "x",
        "job_type": "rewrite_data_files",
        "catalog": "",
        "table": "",
        "job_config": {},
        "cron": "0 2 * * *",
        "status": "paused",
        "next_run_at": None,
        "max_active_runs": 1,
        "created_at": datetime(2026, 4, 10, tzinfo=UTC),
        "updated_at": datetime(2026, 4, 10, tzinfo=UTC),
    }
    assert row_to_job(row).cron == CronExpression(expression="0 2 * * *")
