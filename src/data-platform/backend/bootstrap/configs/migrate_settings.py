"""Define the MigrateSettings configuration model."""

from __future__ import annotations

from pydantic import Field

from bootstrap.configs.database_settings import DatabaseSettings
from bootstrap.configs.role_settings import RoleSettings


class MigrateSettings(RoleSettings):
    """The settings of ``glac migrate``: only the database."""

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
