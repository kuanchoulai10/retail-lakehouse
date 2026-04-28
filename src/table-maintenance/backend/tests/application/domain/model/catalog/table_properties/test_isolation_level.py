"""Test the IsolationLevel enum."""

from __future__ import annotations

from enum import StrEnum

from application.domain.model.catalog.table_properties.isolation_level import (
    IsolationLevel,
)


def test_isolation_level_is_str_enum():
    assert issubclass(IsolationLevel, StrEnum)


def test_serializable_value():
    assert IsolationLevel.SERIALIZABLE == "serializable"


def test_snapshot_value():
    assert IsolationLevel.SNAPSHOT == "snapshot"
