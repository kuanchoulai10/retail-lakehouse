"""Tests for the spark_application_name helper."""

from __future__ import annotations

import re

import pytest

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s import (
    spark_application_name,
)
from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
)
from shared_kernel import prefixed_id_from_parts

DNS_LABEL = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
RUN_ID = "mr-01kaa4zc9qf3v8d2m6xk0w7b1n"


def test_spark_application_name_is_dns_safe_and_deterministic():
    """The application name is deterministic, at most 63 characters and a valid DNS label."""
    for op in MaintenanceOperation:
        first = spark_application_name(RUN_ID, op.value, 12)
        assert first == spark_application_name(RUN_ID, op.value, 12)
        assert len(first) <= 63
        assert DNS_LABEL.match(first)
    assert spark_application_name(RUN_ID, "rewrite_data_files", 1) == "tm-rdf-01kaa4zc9qf3v8d2m6xk0w7b1n-a1"


def test_a_run_id_of_another_shape_is_refused():
    """Only an mr- run id names an application; an old UUID run id is refused."""
    with pytest.raises(ValueError, match="mr-<26 base32 characters>"):
        spark_application_name("3f2504e0-4f89-11d3-9a0c-0305e82c3301", "rewrite_data_files", 1)


def test_codes_per_operation():
    """Each operation has its short code in the name."""
    codes = {op: spark_application_name(RUN_ID, op.value, 1).split("-")[1] for op in MaintenanceOperation}
    assert set(codes.values()) == {"rdf", "rm", "es", "rof"}


def test_attempt_must_be_positive():
    """An attempt number below one is rejected."""
    with pytest.raises(ValueError):
        spark_application_name(RUN_ID, "expire_snapshots", 0)


def test_unknown_operation_is_rejected():
    """An unknown operation name is rejected."""
    with pytest.raises(ValueError):
        spark_application_name(RUN_ID, "defragment", 1)


def test_every_operation_has_a_distinct_code():
    """No two operations share a code."""
    codes = [spark_application_name(RUN_ID, op.value, 1).split("-")[1] for op in MaintenanceOperation]
    assert len(set(codes)) == len(MaintenanceOperation)


def test_spark_application_name_differs_for_runs_in_one_millisecond():
    """Two runs minted in the same millisecond get different names, each a DNS label of at most 63 characters."""
    unix_ms = 1_795_000_000_000
    first, second = (prefixed_id_from_parts("mr", unix_ms, bits) for bits in (1, 2))

    names = {spark_application_name(run_id, op.value, 1) for run_id in (first, second) for op in MaintenanceOperation}

    assert len(names) == 2 * len(MaintenanceOperation)
    assert all(len(name) <= 63 and DNS_LABEL.match(name) for name in names)
