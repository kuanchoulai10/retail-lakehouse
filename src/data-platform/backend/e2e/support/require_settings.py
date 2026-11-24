"""Provide require_settings, which stops a scenario at once when the platform's waits are too long for it."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from e2e.support.platform_api import PlatformApi


def require_settings(platform: PlatformApi, **at_most: int) -> dict[str, int]:
    """Return the named platform settings, failing when one is above its bound.

    A scenario that waits out a quiet period or a cooldown calls this first, so a platform deployed
    with the default values fails it in a second, naming the profile to deploy, instead of after a
    timeout.
    """
    found = {key: platform.platform_setting(key) for key in at_most}
    for key, bound in at_most.items():
        assert found[key] <= bound, (
            f"{key} is {found[key]}, needs at most {bound}: deploy with SETTINGS_PROFILE=e2e "
            "(platform/25-lakehouse-control-plane/bootstrap.sh)"
        )
    return found
