"""Define the DatabaseSettings configuration model."""

from __future__ import annotations

from pydantic import Field

from bootstrap.configs.database_backend import DatabaseBackend
from bootstrap.configs.postgres_settings import PostgresSettings
from bootstrap.configs.settings_block import SettingsBlock
from bootstrap.configs.sqlite_settings import SqliteSettings


class DatabaseSettings(SettingsBlock):
    """Which SQL database holds the control plane's state, and how to reach it.

    The PostgreSQL URL holds the password, so it comes from the environment
    (``GLAC_DATABASE__POSTGRES__DB_URL``), never from the settings file.
    """

    backend: DatabaseBackend = DatabaseBackend.POSTGRES
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    sqlite: SqliteSettings = Field(default_factory=SqliteSettings)
