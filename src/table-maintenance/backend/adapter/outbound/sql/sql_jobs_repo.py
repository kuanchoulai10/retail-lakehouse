from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, insert, select, update

from adapter.outbound.sql.job_to_values import job_to_values
from adapter.outbound.sql.jobs_table import jobs_table
from adapter.outbound.sql.row_to_job import row_to_job
from application.domain.model.job import JobNotFoundError
from application.port.outbound.jobs_repo import BaseJobsRepo

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from application.domain.model.job import Job
    from base.entity_id import EntityId


class SqlJobsRepo(BaseJobsRepo):
    """BaseJobsRepo backed by a SQLAlchemy Engine (Postgres / SQLite / MySQL)."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create(self, entity: Job) -> Job:
        with self._engine.begin() as conn:
            conn.execute(insert(jobs_table).values(**job_to_values(entity)))
        return entity

    def get(self, entity_id: EntityId) -> Job:
        stmt = select(jobs_table).where(jobs_table.c.id == entity_id.value)
        with self._engine.connect() as conn:
            row = conn.execute(stmt).mappings().first()
        if row is None:
            raise JobNotFoundError(entity_id.value)
        return row_to_job(row)

    def list_all(self) -> list[Job]:
        with self._engine.connect() as conn:
            rows = conn.execute(select(jobs_table)).mappings().all()
        return [row_to_job(r) for r in rows]

    def delete(self, entity_id: EntityId) -> None:
        stmt = delete(jobs_table).where(jobs_table.c.id == entity_id.value)
        with self._engine.begin() as conn:
            result = conn.execute(stmt)
        if result.rowcount == 0:
            raise JobNotFoundError(entity_id.value)

    def update(self, entity: Job) -> Job:
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
