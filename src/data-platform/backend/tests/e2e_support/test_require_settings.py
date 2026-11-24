"""Test require_settings, which stops a scenario at once when the platform runs waits too long for it."""

from __future__ import annotations

import httpx
import pytest

from e2e.support import PlatformApi, require_settings

SETTINGS = {
    "groups": [
        {
            "key": "cooldown_and_backoff",
            "items": [{"key": "maintenance_rewrite_data_files_cooldown_seconds", "value": 60}],
        },
        {"key": "partition_selection", "items": [{"key": "maintenance_compaction_quiet_seconds", "value": 120}]},
    ]
}


def _platform() -> PlatformApi:
    return PlatformApi(
        httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=SETTINGS)), base_url="http://api"
        )
    )


def test_settings_within_bounds_are_returned():
    """The scenario gets the values it may wait on."""
    assert require_settings(_platform(), maintenance_rewrite_data_files_cooldown_seconds=60) == {
        "maintenance_rewrite_data_files_cooldown_seconds": 60
    }


def test_a_setting_over_its_bound_names_the_profile_to_deploy():
    """A platform on the default values fails the scenario before it waits for anything."""
    with pytest.raises(
        AssertionError, match=r"maintenance_compaction_quiet_seconds is 120, needs at most 60: .*SETTINGS_PROFILE=e2e"
    ):
        require_settings(
            _platform(), maintenance_rewrite_data_files_cooldown_seconds=60, maintenance_compaction_quiet_seconds=60
        )
