"""Test the ParquetProperties value object."""

from __future__ import annotations

from base.value_object import ValueObject
from application.domain.model.catalog.table_properties.parquet_properties import (
    ParquetProperties,
)


def test_is_value_object():
    assert issubclass(ParquetProperties, ValueObject)


def test_all_defaults_none():
    p = ParquetProperties()
    assert p.compression_codec is None
    assert p.compression_level is None
    assert p.row_group_size_bytes is None
    assert p.page_size_bytes is None
    assert p.dict_size_bytes is None


def test_with_values():
    p = ParquetProperties(
        compression_codec="zstd",
        compression_level=3,
        row_group_size_bytes=134217728,
        page_size_bytes=1048576,
        dict_size_bytes=2097152,
    )
    assert p.compression_codec == "zstd"
    assert p.compression_level == 3
    assert p.row_group_size_bytes == 134217728


def test_frozen():
    p = ParquetProperties()
    import pytest

    with pytest.raises(AttributeError):
        object.__setattr__(p, "compression_codec", "snappy")
