"""Test the DistributionMode enum."""

from __future__ import annotations

from enum import StrEnum

from application.domain.model.catalog.table_properties.distribution_mode import (
    DistributionMode,
)


def test_distribution_mode_is_str_enum():
    assert issubclass(DistributionMode, StrEnum)


def test_none_value():
    assert DistributionMode.NONE == "none"


def test_hash_value():
    assert DistributionMode.HASH == "hash"


def test_range_value():
    assert DistributionMode.RANGE == "range"
