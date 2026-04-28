"""Test the DeleteProperties value object."""

from __future__ import annotations

from base.value_object import ValueObject
from application.domain.model.catalog.table_properties.delete_properties import (
    DeleteProperties,
)
from application.domain.model.catalog.table_properties.distribution_mode import (
    DistributionMode,
)
from application.domain.model.catalog.table_properties.isolation_level import (
    IsolationLevel,
)
from application.domain.model.catalog.table_properties.parquet_properties import (
    ParquetProperties,
)
from application.domain.model.catalog.table_properties.write_mode import WriteMode


def test_is_value_object():
    assert issubclass(DeleteProperties, ValueObject)


def test_all_defaults_none():
    p = DeleteProperties()
    assert p.mode is None
    assert p.isolation_level is None
    assert p.distribution_mode is None
    assert p.format_default is None
    assert p.target_file_size_bytes is None
    assert p.parquet is None


def test_with_nested_parquet():
    p = DeleteProperties(
        mode=WriteMode.COPY_ON_WRITE,
        isolation_level=IsolationLevel.SERIALIZABLE,
        distribution_mode=DistributionMode.RANGE,
        format_default="parquet",
        target_file_size_bytes=67108864,
        parquet=ParquetProperties(compression_codec="zstd"),
    )
    assert p.mode == WriteMode.COPY_ON_WRITE
    assert p.format_default == "parquet"
    assert p.parquet is not None
    assert p.parquet.compression_codec == "zstd"
