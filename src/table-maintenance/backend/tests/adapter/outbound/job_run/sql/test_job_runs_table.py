"""Tests for job_runs_table."""

from __future__ import annotations

from core.adapter.outbound.job_run.sql.job_runs_table import job_runs_table
from core.adapter.outbound.sql.metadata import metadata


def test_table_exists_in_shared_metadata():
    """Verify that the job_runs table is registered in shared metadata."""
    assert "job_runs" in metadata.tables


def test_columns():
    """Verify that the table has the expected columns."""
    cols = {c.name for c in job_runs_table.columns}
    assert cols == {
        "id",
        "job_id",
        "status",
        "trigger_type",
        "started_at",
        "finished_at",
    }


def test_primary_key_is_id():
    """Verify that the primary key is the id column."""
    assert job_runs_table.c.id.primary_key


def test_job_id_has_foreign_key_to_jobs():
    """Verify that job_id has a foreign key referencing jobs.id."""
    fks = {fk.target_fullname for fk in job_runs_table.c.job_id.foreign_keys}
    assert "jobs.id" in fks
