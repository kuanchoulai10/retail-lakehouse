"""Test the GetPlatformSettingsService."""

from __future__ import annotations

import re
from typing import Any

import pytest

from context.table_maintenance.application.domain.model.shared import (
    ComputeSize,
    PlatformComputeSize,
    PlatformPriority,
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
        "round_seconds": 120,
        "budget_gb_hours": 0.05,
        "priorities": (
            PlatformPriority(priority="P0", weight=4.0, sla_seconds=3600),
            PlatformPriority(priority="P1", weight=2.0, sla_seconds=14400),
            PlatformPriority(priority="P2", weight=1.0, sla_seconds=28800),
        ),
        "grant_lease_seconds": 600,
        "partitions_per_run": 10,
        "quiet_seconds": 120,
        "max_quiet_wait_seconds": 3600,
        "min_partition_bytes": 0,
        "failure_backoff_cap_seconds": 86400,
        "discovery_interval_seconds": 600,
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
        ("compaction_scheduling", "Compaction scheduling"),
        ("cooldown_and_backoff", "Cooldown and backoff"),
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


def test_compaction_scheduling_reports_the_round_the_weights_and_the_filters():
    """The compaction group lists the round interval and budget, each priority, the grant lease and the filters."""
    group = _output().groups[2]

    assert [(i.key, i.value, i.unit) for i in group.items] == [
        ("scheduler_round_seconds", 120, "seconds"),
        ("scheduler_budget_gb_hours", 0.05, "GB·hours"),
        ("scheduler_priority_weight_p0", 4.0, "times"),
        ("scheduler_priority_weight_p1", 2.0, "times"),
        ("scheduler_priority_weight_p2", 1.0, "times"),
        ("scheduler_sla_seconds_p0", 3600, "seconds"),
        ("scheduler_sla_seconds_p1", 14400, "seconds"),
        ("scheduler_sla_seconds_p2", 28800, "seconds"),
        ("scheduler_grant_lease_seconds", 600, "seconds"),
        ("compaction_partitions_per_run", 10, "partitions"),
        ("compaction_quiet_seconds", 120, "seconds"),
        ("compaction_max_quiet_wait_seconds", 3600, "seconds"),
        ("compaction_min_partition_bytes", 0, "bytes"),
    ]


def test_cooldown_and_discovery_report_their_one_setting_each():
    """The failure backoff cap and the discovery scan interval each have a group of their own."""
    output = _output(failure_backoff_cap_seconds=3600, discovery_interval_seconds=60)

    assert [(i.key, i.value, i.unit) for i in output.groups[3].items] == [
        ("maintenance_failure_backoff_cap_seconds", 3600, "seconds")
    ]
    assert [(i.key, i.value, i.unit) for i in output.groups[4].items] == [("discovery_interval_seconds", 60, "seconds")]


def test_values_follow_the_settings_they_were_built_from():
    """Nothing is fixed in the service: a changed setting shows as the changed value."""
    assert _values(_output(round_seconds=30, partitions_per_run=7))["scheduler_round_seconds"] == 30
    assert _values(_output(round_seconds=30, partitions_per_run=7))["compaction_partitions_per_run"] == 7


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
