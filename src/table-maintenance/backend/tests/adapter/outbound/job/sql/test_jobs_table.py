"""Tests for jobs_table."""

from sqlalchemy import DateTime, String

from adapter.outbound.job.sql.jobs_table import jobs_table


def test_table_name():
    """Verify that the table name is 'jobs'."""
    assert jobs_table.name == "jobs"


def test_primary_key_is_id():
    """Verify that the primary key is the id column."""
    pks = [c.name for c in jobs_table.primary_key]
    assert pks == ["id"]


def test_has_expected_columns():
    """Verify that the table has all expected columns."""
    names = {c.name for c in jobs_table.columns}
    assert names == {
        "id",
        "job_type",
        "catalog",
        "table",
        "job_config",
        "cron",
        "status",
        "next_run_at",
        "max_active_runs",
        "driver_memory",
        "executor_memory",
        "executor_instances",
        "created_at",
        "updated_at",
    }


def test_id_is_string_not_null():
    """Verify that the id column is a non-nullable string."""
    col = jobs_table.c.id
    assert isinstance(col.type, String)
    assert col.nullable is False


def test_status_is_string():
    """Verify that the status column is a string type."""
    assert isinstance(jobs_table.c.status.type, String)


def test_cron_is_nullable():
    """Verify that the cron column is nullable."""
    assert jobs_table.c.cron.nullable is True


def test_timestamps_are_tz_aware():
    """Verify that timestamp columns are timezone-aware DateTime."""
    assert isinstance(jobs_table.c.created_at.type, DateTime)
    assert jobs_table.c.created_at.type.timezone is True
    assert isinstance(jobs_table.c.updated_at.type, DateTime)
    assert jobs_table.c.updated_at.type.timezone is True
