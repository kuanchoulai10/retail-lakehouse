"""Define the JobsSqlRepo adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, insert, select, update

from adapter.outbound.job.sql.job_to_values import job_to_values
from adapter.outbound.job.sql.jobs_table import jobs_table
from adapter.outbound.job.sql.row_to_job import row_to_job
from application.domain.model.job import JobNotFoundError
from application.port.outbound.job.jobs_repo import JobsRepo

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy import Engine

    from application.domain.model.job import Job, JobId
    from base.entity_id import EntityId


class JobsSqlRepo(JobsRepo):
    """JobsRepo backed by a SQLAlchemy Engine (Postgres / SQLite / MySQL)."""

    def __init__(self, engine: Engine) -> None:
        """Initialize the repository with a SQLAlchemy engine."""
        self._engine = engine

    def create(self, entity: Job) -> Job:
        """Insert a new job row and return the entity."""
        with self._engine.begin() as conn:
            conn.execute(insert(jobs_table).values(**job_to_values(entity)))
        return entity

    def get(self, entity_id: EntityId) -> Job:
        """Fetch a job by id or raise JobNotFoundError."""
        stmt = select(jobs_table).where(jobs_table.c.id == entity_id.value)
        with self._engine.connect() as conn:
            row = conn.execute(stmt).mappings().first()
        if row is None:
            raise JobNotFoundError(entity_id.value)
        return row_to_job(row)

    def list_all(self) -> list[Job]:
        """Return all jobs from the database."""
        with self._engine.connect() as conn:
            rows = conn.execute(select(jobs_table)).mappings().all()
        return [row_to_job(r) for r in rows]

    def delete(self, entity_id: EntityId) -> None:
        """Delete a job by id or raise JobNotFoundError."""
        stmt = delete(jobs_table).where(jobs_table.c.id == entity_id.value)
        with self._engine.begin() as conn:
            result = conn.execute(stmt)
        if result.rowcount == 0:
            raise JobNotFoundError(entity_id.value)

    def update(self, entity: Job) -> Job:
        """Update an existing job row or raise JobNotFoundError."""
        stmt = (
            update(jobs_table)
            .where(jobs_table.c.id == entity.id.value)
            .values(**job_to_values(entity))
        )
        with self._engine.begin() as conn:
            result = conn.execute(stmt)
        if result.rowcount == 0:
            raise JobNotFoundError(entity.id.value)
        return entity

    def list_schedulable(self, now: datetime) -> list[Job]:
        """Return enabled jobs with a cron schedule whose next_run_at <= now."""
        stmt = select(jobs_table).where(
            jobs_table.c.status == "active",
            jobs_table.c.cron.isnot(None),
            jobs_table.c.next_run_at.isnot(None),
            jobs_table.c.next_run_at <= now,
        )
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [row_to_job(r) for r in rows]

    def save_next_run_at(self, job_id: JobId, next_run_at: datetime) -> None:
        """Persist the advanced next_run_at for a job."""
        stmt = (
            update(jobs_table)
            .where(jobs_table.c.id == job_id.value)
            .values(next_run_at=next_run_at)
        )
        with self._engine.begin() as conn:
            result = conn.execute(stmt)
        if result.rowcount == 0:
            raise JobNotFoundError(job_id.value)
