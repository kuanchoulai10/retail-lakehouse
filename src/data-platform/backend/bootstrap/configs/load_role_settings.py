"""Provide the load_role_settings function."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import yaml
from pydantic_settings import CliApp

from bootstrap.configs.reject_unknown_environment import reject_unknown_environment
from bootstrap.configs.role_settings import CONFIG_FILE, RoleSettings
from bootstrap.configs.setting_paths import setting_paths
from bootstrap.configs.unknown_setting_error import UnknownSettingError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path


def load_role_settings[R: RoleSettings](
    settings_cls: type[R],
    *,
    config_file: Path | None,
    cli_args: Sequence[str] = (),
    environ: Mapping[str, str] = os.environ,
) -> R:
    """Return the role's settings from its flags, the environment, its settings file and the defaults, in that order.

    Raises ``UnknownSettingError`` for a ``GLAC_`` variable the role does not take, a settings file that is
    missing or not a mapping, and a secret written in the file; a misspelt key in the file fails validation
    and a misspelt flag exits with a usage error.
    """
    reject_unknown_environment(settings_cls, environ)
    if config_file is not None:
        _check_config_file(settings_cls, config_file)
    token = CONFIG_FILE.set(config_file)
    try:
        return CliApp.run(settings_cls, cli_args=list(cli_args))
    finally:
        CONFIG_FILE.reset(token)


def _check_config_file(settings_cls: type[RoleSettings], config_file: Path) -> None:
    if not config_file.is_file():
        msg = f"settings file {config_file} does not exist"
        raise UnknownSettingError(msg)
    content = yaml.safe_load(config_file.read_text())
    if content is None:
        return
    if not isinstance(content, dict):
        msg = f"settings file {config_file} must hold a mapping at its top level"
        raise UnknownSettingError(msg)
    for path, secret in setting_paths(settings_cls):
        if secret and _holds(content, path):
            msg = f"settings file {config_file} sets the secret {'.'.join(path)}; secrets come from the environment"
            raise UnknownSettingError(msg)


def _holds(content: dict[str, Any], path: tuple[str, ...]) -> bool:
    node: Any = content
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return False
        node = node[key]
    return True
