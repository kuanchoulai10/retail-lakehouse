"""Define the RoleSettings base class and the settings file it reads."""

from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING

from pydantic_settings import BaseSettings, SettingsConfigDict, YamlConfigSettingsSource

if TYPE_CHECKING:
    from pathlib import Path

    from pydantic_settings import PydanticBaseSettingsSource

CONFIG_FILE: ContextVar[Path | None] = ContextVar("CONFIG_FILE", default=None)


class RoleSettings(BaseSettings):
    """The settings of one role (one ``glac`` subcommand), read by ``load_role_settings``.

    Command-line flags win over ``GLAC_`` environment variables (nested with ``__``), which
    win over the YAML settings file in ``CONFIG_FILE``, which wins over the defaults here.
    A key or flag the role does not know is refused.
    """

    model_config = SettingsConfigDict(
        env_prefix="GLAC_",
        env_nested_delimiter="__",
        extra="forbid",
        cli_kebab_case=True,
        cli_implicit_flags=True,
    )

    log_level: str = "INFO"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,  # noqa: ARG003
        file_secret_settings: PydanticBaseSettingsSource,  # noqa: ARG003
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Read the flags (passed as init values), then the environment, then the settings file."""
        return (init_settings, env_settings, YamlConfigSettingsSource(settings_cls, yaml_file=CONFIG_FILE.get()))
