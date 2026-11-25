"""Maintenance policies describe a target state; the platform owns the cooldowns and the options it sets itself."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from e2e.support import OwnedNames, assert_prefixed_ids

if TYPE_CHECKING:
    import httpx

    from e2e.support import CleanupStack, E2eSettings, PlatformApi

pytestmark = pytest.mark.critical

POLICIES = "/v1/maintenance-policies"
CONTENT = (
    "description",
    "on",
    "dry_run",
    "rewrite_data_files",
    "rewrite_manifests",
    "expire_snapshots",
    "remove_orphan_files",
)
COOLDOWNS = (
    "maintenance_rewrite_data_files_cooldown_seconds",
    "maintenance_rewrite_manifests_cooldown_seconds",
    "maintenance_expire_snapshots_cooldown_seconds",
    "maintenance_remove_orphan_files_interval_seconds",
)


def test_the_default_policy_has_the_target_state_shape(platform: PlatformApi):
    """Triggers, dry run and one block per operation; its values are the seeded ones while nobody edited it."""
    default = platform.get(f"{POLICIES}/default")
    assert set(default) == {"id", "name", "is_default", "version", "created_at", "updated_at", *CONTENT}
    assert default["is_default"] is True
    assert_prefixed_ids({"mp": [default["id"]]})
    if default["version"] != 1:
        return
    assert default["on"] == {"schedule": {"every_seconds": 3600}, "catalog_commit": {"debounce_seconds": 300}}
    assert default["dry_run"] is False
    assert default["rewrite_data_files"] == {
        "target": {"reducible_files": {"at_most": 5}, "per": "partition"},
        "options": {"min_input_files": 2, "partial_progress_enabled": True},
    }
    assert default["rewrite_manifests"]["target"] == {"small_manifests": {"at_most": 5}}
    assert default["expire_snapshots"]["target"] == {"min_snapshots_to_keep": 10, "max_snapshot_age_seconds": 86400}
    assert default["remove_orphan_files"]["target"] == {"older_than_seconds": 259200}


def test_the_platform_settings_list_the_four_cooldowns(platform: PlatformApi):
    """The cooldowns are platform settings, not policy content; their values belong to the chart."""
    for key in (*COOLDOWNS, "discovery_interval_seconds"):
        value = platform.platform_setting(key)
        assert type(value) is int and value >= 0, f"{key} is {value!r}"


def test_an_option_the_platform_owns_or_does_not_know_is_refused(
    api: httpx.Client, platform: PlatformApi, suffix: str, cleanup: CleanupStack
):
    """``retain_last`` is set by the platform from the target, and an unknown option is no option: both are 422."""
    default = platform.get(f"{POLICIES}/default")
    body = {key: default[key] for key in CONTENT}
    refused = {
        "owned": {"expire_snapshots": {"target": {"min_snapshots_to_keep": 10}, "options": {"retain_last": 5}}},
        "unknown": {"rewrite_manifests": {"target": {"small_manifests": {"at_most": 5}}, "options": {"no_such": True}}},
    }
    for scenario, change in refused.items():
        name = OwnedNames.maintenance_policy(suffix, scenario)
        cleanup.push(f"delete {name}", lambda name=name: _delete_if_present(api, f"{POLICIES}/{name}"))
        reply = api.post(POLICIES, json={**body, **change, "name": name})
        assert reply.status_code == 422, f"{scenario}: {reply.status_code} {reply.text}"
        assert api.get(f"{POLICIES}/{name}").status_code == 404
    assert not {policy["name"] for policy in platform.get(POLICIES)["policies"]} & {
        OwnedNames.maintenance_policy(suffix, scenario) for scenario in refused
    }


def _delete_if_present(api: httpx.Client, path: str) -> None:
    reply = api.delete(path)
    assert reply.status_code in (204, 404), f"DELETE {path} answered {reply.status_code}: {reply.text}"


def test_the_partition_selection_settings_are_the_deployed_ones(platform: PlatformApi, settings: E2eSettings):
    """Partition selection sits between the cooldowns and discovery, showing every value the worker was given.

    The worker runs the backend's default for what its settings file leaves out, so under the default
    profile only the group's keys are compared; the e2e profile sets two of its values.
    """
    groups = platform.get("/v1/platform-settings")["groups"]
    assert [group["key"] for group in groups] == [
        "execution_capacity",
        "compute_sizes",
        "cooldown_and_backoff",
        "partition_selection",
        "discovery",
    ]
    [selection] = [group for group in groups if group["key"] == "partition_selection"]
    shown = {item["key"]: item["value"] for item in selection["items"]}
    assert set(shown) == {
        f"maintenance_compaction_{key}" for key in ("partitions_per_job", "quiet_seconds", "max_quiet_wait_seconds")
    }
    given = {
        f"maintenance_{key}": value
        for key, value in settings.worker_maintenance.items()
        if key.startswith("compaction_")
    }
    assert {key: shown[key] for key in given} == given
