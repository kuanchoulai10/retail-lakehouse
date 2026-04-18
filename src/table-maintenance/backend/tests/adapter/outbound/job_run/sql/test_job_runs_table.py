from __future__ import annotations

from adapter.outbound.job_run.sql.job_runs_table import job_runs_table
from adapter.outbound.sql.metadata import metadata


def test_table_exists_in_shared_metadata():
    assert "job_runs" in metadata.tables


def test_columns():
    cols = {c.name for c in job_runs_table.columns}
    assert cols == {"id", "job_id", "status", "started_at", "finished_at"}


def test_primary_key_is_id():
    assert job_runs_table.c.id.primary_key


def test_job_id_has_foreign_key_to_jobs():
    fks = {fk.target_fullname for fk in job_runs_table.c.job_id.foreign_keys}
    assert "jobs.id" in fks
