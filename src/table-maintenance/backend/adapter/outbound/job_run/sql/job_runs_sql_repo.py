"""Define the JobRunsSqlRepo adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, insert, select, update

from adapter.outbound.job_run.sql.job_run_to_values import job_run_to_values
from adapter.outbound.job_run.sql.job_runs_table import job_runs_table
from adapter.outbound.job_run.sql.row_to_job_run import row_to_job_run
from application.domain.model.job_run import JobRunNotFoundError
from application.port.outbound.job_run.job_runs_repo import JobRunsRepo

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from base.entity_id import EntityId

    from application.domain.model.job import JobId
    from application.domain.model.job_run import JobRun


class JobRunsSqlRepo(JobRunsRepo):
    """JobRunsRepo backed by a SQLAlchemy Engine."""

    def __init__(self, engine: Engine) -> None:
        """Initialize the repository with a SQLAlchemy engine."""
        self._engine = engine

    def create(self, entity: JobRun) -> JobRun:
        """Insert a new job run row and return the entity."""
        with self._engine.begin() as conn:
            conn.execute(insert(job_runs_table).values(**job_run_to_values(entity)))
        return entity

    def save(self, entity: JobRun) -> JobRun:
        """Update an existing job run row and return the entity."""
        values = job_run_to_values(entity)
        run_id = values.pop("id")
        stmt = (
            update(job_runs_table).where(job_runs_table.c.id == run_id).values(**values)
        )
        with self._engine.begin() as conn:
            conn.execute(stmt)
        return entity

    def get(self, entity_id: EntityId) -> JobRun:
        """Fetch a job run by id or raise JobRunNotFoundError."""
        stmt = select(job_runs_table).where(job_runs_table.c.id == entity_id.value)
        with self._engine.connect() as conn:
            row = conn.execute(stmt).mappings().first()
        if row is None:
            raise JobRunNotFoundError(entity_id.value)
        return row_to_job_run(row)

    def list_for_job(self, job_id: JobId) -> list[JobRun]:
        """Return all job runs belonging to the given job."""
        stmt = select(job_runs_table).where(job_runs_table.c.job_id == job_id.value)
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [row_to_job_run(r) for r in rows]

    def list_all(self) -> list[JobRun]:
        """Return all job runs from the database."""
        with self._engine.connect() as conn:
            rows = conn.execute(select(job_runs_table)).mappings().all()
        return [row_to_job_run(r) for r in rows]

    def count_active_for_job(self, job_id: JobId) -> int:
        """Return the count of non-terminal runs (pending or running) for a job."""
        stmt = (
            select(func.count())
            .select_from(job_runs_table)
            .where(
                job_runs_table.c.job_id == job_id.value,
                job_runs_table.c.status.in_(["pending", "running"]),
            )
        )
        with self._engine.connect() as conn:
            return conn.execute(stmt).scalar_one()
