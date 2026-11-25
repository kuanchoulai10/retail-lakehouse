"""Provide the reject_unknown_environment function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bootstrap.configs.setting_paths import setting_paths
from bootstrap.configs.unknown_setting_error import UnknownSettingError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from bootstrap.configs.role_settings import RoleSettings

PREFIX = "GLAC_"
DELIMITER = "__"


def reject_unknown_environment(settings_cls: type[RoleSettings], environ: Mapping[str, str]) -> None:
    """Raise ``UnknownSettingError`` naming every ``GLAC_`` variable that sets no field of ``settings_cls``.

    pydantic-settings ignores such a variable, so a misspelt one would leave the default in place.
    A variable may name a field at any depth, a whole block included; names compare in any case.
    """
    known = {PREFIX + DELIMITER.join(path).upper() for path, _secret in setting_paths(settings_cls)}
    unknown = sorted(name for name in environ if name.upper().startswith(PREFIX) and name.upper() not in known)
    if unknown:
        msg = f"{settings_cls.__name__} takes no setting {', '.join(unknown)}"
        raise UnknownSettingError(msg)
