"""Tests for the spark_application_name helper."""

from __future__ import annotations

import re

import pytest

from application.domain.model.maintenance.maintenance_operation import (
    MaintenanceOperation,
)
from adapter.outbound.table_maintenance_run.k8s.spark_application_name import (
    spark_application_name,
)

DNS_LABEL = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")


def test_spark_application_name_is_dns_safe_and_deterministic():
    run_id = "3F2504E0-4F89-11D3-9A0C-0305E82C3301-EXTRA-LONG-SUFFIX"
    for op in MaintenanceOperation:
        first = spark_application_name(run_id, op.value, 12)
        assert first == spark_application_name(run_id, op.value, 12)
        assert len(first) <= 63
        assert DNS_LABEL.match(first)
    assert (
        spark_application_name("abc-def", "rewrite_data_files", 1) == "tm-rdf-abcdef-a1"
    )


def test_codes_per_operation():
    codes = {
        op: spark_application_name("r", op.value, 1).split("-")[1]
        for op in MaintenanceOperation
    }
    assert set(codes.values()) == {"rdf", "rm", "es", "rof"}


def test_attempt_must_be_positive():
    with pytest.raises(ValueError):
        spark_application_name("r", "expire_snapshots", 0)


def test_unknown_operation_is_rejected():
    with pytest.raises(ValueError):
        spark_application_name("r", "defragment", 1)
