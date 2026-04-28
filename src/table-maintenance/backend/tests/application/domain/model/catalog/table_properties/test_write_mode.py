"""Test the WriteMode enum."""

from __future__ import annotations

from enum import StrEnum

from application.domain.model.catalog.table_properties.write_mode import WriteMode


def test_write_mode_is_str_enum():
    assert issubclass(WriteMode, StrEnum)


def test_copy_on_write_value():
    assert WriteMode.COPY_ON_WRITE == "copy-on-write"


def test_merge_on_read_value():
    assert WriteMode.MERGE_ON_READ == "merge-on-read"


def test_from_string():
    assert WriteMode("copy-on-write") is WriteMode.COPY_ON_WRITE
