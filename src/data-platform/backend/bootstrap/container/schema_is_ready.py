"""Provide the schema_is_ready function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.exc import OperationalError, ProgrammingError

from bootstrap.container.build_repositories import build_repositories
from context.table_maintenance.application.domain.model.table_maintenance_policy import DEFAULT_POLICY_ID

if TYPE_CHECKING:
    from sqlalchemy import Engine


def schema_is_ready(engine: Engine) -> bool:
    """Return whether the migrations have run: the default maintenance policy exists.

    A database that cannot be reached yet, or has no tables yet, is not ready.
    """
    repositories = build_repositories(engine)
    try:
        return repositories.table_maintenance_policies.get(DEFAULT_POLICY_ID) is not None
    except OperationalError, ProgrammingError:
        return False
