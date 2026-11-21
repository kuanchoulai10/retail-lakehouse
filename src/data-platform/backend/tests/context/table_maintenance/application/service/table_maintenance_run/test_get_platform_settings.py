"""Test the GetPlatformSettingsService."""

from __future__ import annotations

import re
from typing import Any

import pytest

from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    PlatformComputeSize,
    PlatformSettings,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    GetPlatformSettingsUseCaseInput,
    GetPlatformSettingsUseCaseOutput,
)
from context.table_maintenance.application.service.table_maintenance_run import GetPlatformSettingsService

SECRET_WORDS = ("password", "secret", "key", "token", "credential")
USERINFO_URI = re.compile(r"[a-z][a-z0-9+.-]*://[^/\s]*@", re.IGNORECASE)


def _settings(**changes: Any) -> PlatformSettings:  # noqa: ANN401
    values: dict[str, Any] = {
        "attempt_deadline_seconds": 21600,
        "max_attempts": 3,
        "queue_wait_limit_seconds": 86400,
        "compute_sizes": (
            PlatformComputeSize(size=ComputeSize.S, driver_memory="768m", executor_memory="768m", executor_instances=1),
            PlatformComputeSize(size=ComputeSize.M, driver_memory="1g", executor_memory="1536m", executor_instances=1),
            PlatformComputeSize(size=ComputeSize.L, driver_memory="1536m", executor_memory="2g", executor_instances=2),
        ),
        "rewrite_data_files_cooldown_seconds": 3600,
        "rewrite_manifests_cooldown_seconds": 21600,
        "expire_snapshots_cooldown_seconds": 21600,
        "remove_orphan_files_interval_seconds": 604800,
        "failure_backoff_cap_seconds": 86400,
        "discovery_interval_seconds": 600,
        "compaction_partitions_per_job": 10,
        "compaction_quiet_seconds": 120,
        "compaction_max_quiet_wait_seconds": 3600,
    }
    return PlatformSettings(**{**values, **changes})


def _output(**changes: Any) -> GetPlatformSettingsUseCaseOutput:
    return GetPlatformSettingsService(_settings(**changes)).execute(GetPlatformSettingsUseCaseInput())


def _values(output: GetPlatformSettingsUseCaseOutput) -> dict[str, object]:
    return {item.key: item.value for group in output.groups for item in group.items}


def test_groups_follow_the_page_order_with_a_key_and_a_title():
    """The settings come in five groups, each with a stable key and a title, in the order the page shows them."""
    output = _output()

    assert [(g.key, g.title) for g in output.groups] == [
        ("execution_capacity", "Execution capacity"),
        ("compute_sizes", "Spark sizes"),
        ("cooldown_and_backoff", "Cooldown and backoff"),
        ("partition_selection", "Compaction partition selection"),
        ("discovery", "Discovery"),
    ]


def test_execution_capacity_reports_the_deadline_the_queue_wait_limit_and_attempts():
    """The execution capacity group lists the attempt time limit, the queue wait limit and the attempts."""
    group = _output(attempt_deadline_seconds=120, queue_wait_limit_seconds=600, max_attempts=5).groups[0]

    assert [(i.key, i.value, i.unit) for i in group.items] == [
        ("maintenance_attempt_deadline_seconds", 120, "seconds"),
        ("maintenance_queue_wait_limit_seconds", 600, "seconds"),
        ("maintenance_max_attempts", 5, "attempts"),
    ]


def test_compute_sizes_list_memory_and_executors_of_each_size():
    """Each Spark size lists its driver memory, executor memory and executor count."""
    group = _output().groups[1]

    assert [(i.key, i.value, i.unit) for i in group.items] == [
        ("compute_size_s_driver_memory", "768m", None),
        ("compute_size_s_executor_memory", "768m", None),
        ("compute_size_s_executor_instances", 1, "executors"),
        ("compute_size_m_driver_memory", "1g", None),
        ("compute_size_m_executor_memory", "1536m", None),
        ("compute_size_m_executor_instances", 1, "executors"),
        ("compute_size_l_driver_memory", "1536m", None),
        ("compute_size_l_executor_memory", "2g", None),
        ("compute_size_l_executor_instances", 2, "executors"),
    ]


def test_platform_settings_list_the_cooldowns():
    """The cooldown group lists the three cooldowns, the orphan file interval and the failure backoff cap, in order."""
    output = _output(
        rewrite_data_files_cooldown_seconds=60,
        rewrite_manifests_cooldown_seconds=120,
        expire_snapshots_cooldown_seconds=180,
        remove_orphan_files_interval_seconds=240,
        failure_backoff_cap_seconds=3600,
    )

    assert [(i.key, i.label, i.value, i.unit) for i in output.groups[2].items] == [
        ("maintenance_rewrite_data_files_cooldown_seconds", "Rewrite data files cooldown", 60, "seconds"),
        ("maintenance_rewrite_manifests_cooldown_seconds", "Rewrite manifests cooldown", 120, "seconds"),
        ("maintenance_expire_snapshots_cooldown_seconds", "Expire snapshots cooldown", 180, "seconds"),
        ("maintenance_remove_orphan_files_interval_seconds", "Orphan file removal interval", 240, "seconds"),
        ("maintenance_failure_backoff_cap_seconds", "Failure backoff cap", 3600, "seconds"),
    ]
    assert [i.description for i in output.groups[2].items][:4] == [
        "The least time between two runs of rewrite data files on one table.",
        "The least time between two runs of rewrite manifests on one table.",
        "The least time between two runs of expire snapshots on one table.",
        "How often orphan files are removed from a table: they have no target the platform can measure.",
    ]


def test_platform_settings_list_partition_selection():
    """The partition selection group lists the cap, the quiet period and the longest wait, with their wording."""
    groups = _output().groups

    assert [g.key for g in groups] == [
        "execution_capacity",
        "compute_sizes",
        "cooldown_and_backoff",
        "partition_selection",
        "discovery",
    ]
    assert groups[3].title == "Compaction partition selection"
    assert [(i.key, i.label, i.value, i.unit, i.description) for i in groups[3].items] == [
        (
            "maintenance_compaction_partitions_per_job",
            "Partitions per job",
            10,
            "partitions",
            "The most partitions one rewrite data files job compacts; those over the target for the longest wait go "
            "first, oldest first, then the ones with the most reducible files; the rest wait for a later check.",
        ),
        (
            "maintenance_compaction_quiet_seconds",
            "Quiet period",
            120,
            "seconds",
            "A partition written more recently than this waits for a later check, so compaction does not race its "
            "writers.",
        ),
        (
            "maintenance_compaction_max_quiet_wait_seconds",
            "Longest wait for quiet",
            3600,
            "seconds",
            "A partition over its target for this long is compacted even while it is still being written.",
        ),
    ]


def test_partition_selection_values_follow_the_settings():
    """A changed setting shows as the changed value."""
    values = _values(
        _output(compaction_partitions_per_job=4, compaction_quiet_seconds=0, compaction_max_quiet_wait_seconds=600)
    )

    assert values["maintenance_compaction_partitions_per_job"] == 4
    assert values["maintenance_compaction_quiet_seconds"] == 0
    assert values["maintenance_compaction_max_quiet_wait_seconds"] == 600


def test_discovery_reports_its_one_setting():
    """The discovery scan interval has a group of its own."""
    output = _output(discovery_interval_seconds=60)

    assert [(i.key, i.value, i.unit) for i in output.groups[4].items] == [("discovery_interval_seconds", 60, "seconds")]


def test_values_follow_the_settings_they_were_built_from():
    """Nothing is fixed in the service: a changed setting shows as the changed value."""
    values = _values(_output(max_attempts=7, discovery_interval_seconds=30))
    assert values["maintenance_max_attempts"] == 7
    assert values["discovery_interval_seconds"] == 30


def test_every_item_has_a_stable_key_a_label_and_a_one_sentence_description():
    """Keys are unique and snake case, labels are short, and each description is one sentence ending in a period."""
    items = [item for group in _output().groups for item in group.items]

    keys = [item.key for item in items]
    assert len(keys) == len(set(keys))
    assert all(re.fullmatch(r"[a-z0-9_]+", key) for key in keys)
    assert all(item.label and item.label == item.label.strip() for item in items)
    for item in items:
        assert item.description.endswith("."), item.key
        assert ". " not in item.description, item.key


@pytest.mark.parametrize("word", SECRET_WORDS)
def test_nothing_secret_looking_is_listed(word: str):
    """No key, label, unit, description or text value carries a word that names a secret."""
    output = _output()
    texts = [output_text for group in output.groups for output_text in (group.key, group.title)]
    for group in output.groups:
        for item in group.items:
            texts += [item.key, item.label, item.description, item.unit or "", str(item.value)]

    assert not [text for text in texts if word in text.lower()]


def test_no_value_is_a_uri_with_user_info():
    """No listed value is an address with a user name or password in it."""
    values = [str(item.value) for group in _output().groups for item in group.items]

    assert not [value for value in values if USERINFO_URI.search(value)]


def test_the_attempt_limits_say_what_the_queue_wait_counts_toward():
    """The attempt time limit runs from the Spark job's start; the queue wait limit bounds the wait before it."""
    items = {item.key: item for item in _output().groups[0].items}

    assert items["maintenance_attempt_deadline_seconds"].description == (
        "How long one attempt may run once its Spark job has started; time spent waiting in the queue does not count."
    )
    queue = items["maintenance_queue_wait_limit_seconds"]
    assert (queue.label, queue.unit) == ("Queue wait limit", "seconds")
    assert queue.description == (
        "How long one attempt may wait in its Volcano queue before it is stopped; its operation then waits for the "
        "next plan."
    )
