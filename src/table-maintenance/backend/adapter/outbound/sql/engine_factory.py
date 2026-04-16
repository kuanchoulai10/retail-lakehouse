from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import create_engine

from configs import JobsRepoBackend

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from configs import AppSettings


def build_engine(backend: JobsRepoBackend, settings: AppSettings) -> Engine:
    if backend == JobsRepoBackend.SQLITE:
        return create_engine(f"sqlite:///{settings.sqlite.db_path}")
    if backend == JobsRepoBackend.POSTGRES:
        return create_engine(
            settings.postgres.db_url,
            pool_size=settings.postgres.pool_size,
        )
    raise ValueError(
        f"build_engine does not support {backend.value!r}; use an in-process repo for IN_MEMORY"
    )
