"""Test the OperationProperties value object."""

from __future__ import annotations

from base.value_object import ValueObject
from application.domain.model.catalog.table_properties.distribution_mode import (
    DistributionMode,
)
from application.domain.model.catalog.table_properties.isolation_level import (
    IsolationLevel,
)
from application.domain.model.catalog.table_properties.operation_properties import (
    OperationProperties,
)
from application.domain.model.catalog.table_properties.write_mode import WriteMode


def test_is_value_object():
    assert issubclass(OperationProperties, ValueObject)


def test_all_defaults_none():
    p = OperationProperties()
    assert p.mode is None
    assert p.isolation_level is None
    assert p.distribution_mode is None


def test_with_values():
    p = OperationProperties(
        mode=WriteMode.MERGE_ON_READ,
        isolation_level=IsolationLevel.SNAPSHOT,
        distribution_mode=DistributionMode.HASH,
    )
    assert p.mode == WriteMode.MERGE_ON_READ
    assert p.isolation_level == IsolationLevel.SNAPSHOT
    assert p.distribution_mode == DistributionMode.HASH
