"""Define the AppSettings configuration model."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from bootstrap.configs.component import Component
from bootstrap.configs.postgres_settings import PostgresSettings


class AppSettings(BaseSettings):
    """Root application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="GLAC_",
        env_nested_delimiter="__",
    )

    component: Component = Component.API
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
