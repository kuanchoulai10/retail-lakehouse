"""Test the TableProperties composite value object."""

from __future__ import annotations

from base.value_object import ValueObject
from application.domain.model.catalog.table_properties.distribution_mode import (
    DistributionMode,
)
from application.domain.model.catalog.table_properties.operation_properties import (
    OperationProperties,
)
from application.domain.model.catalog.table_properties.delete_properties import (
    DeleteProperties,
)
from application.domain.model.catalog.table_properties.parquet_properties import (
    ParquetProperties,
)
from application.domain.model.catalog.table_properties.read_properties import (
    ReadProperties,
)
from application.domain.model.catalog.table_properties.split_properties import (
    SplitProperties,
)
from application.domain.model.catalog.table_properties.table_properties import (
    TableProperties,
)
from application.domain.model.catalog.table_properties.write_mode import WriteMode
from application.domain.model.catalog.table_properties.write_properties import (
    WriteProperties,
)


def test_table_properties_is_value_object():
    assert issubclass(TableProperties, ValueObject)


def test_all_defaults_none():
    p = TableProperties()
    assert p.format_version is None
    assert p.write is None
    assert p.read is None


def test_full_nested_structure():
    p = TableProperties(
        format_version=2,
        write=WriteProperties(
            merge=OperationProperties(mode=WriteMode.MERGE_ON_READ),
            update=OperationProperties(mode=WriteMode.COPY_ON_WRITE),
            delete=DeleteProperties(
                mode=WriteMode.COPY_ON_WRITE,
                parquet=ParquetProperties(compression_codec="zstd"),
            ),
            distribution_mode=DistributionMode.HASH,
            target_file_size_bytes=536870912,
            upsert_enabled=False,
        ),
        read=ReadProperties(
            split=SplitProperties(size=134217728),
        ),
    )
    assert p.format_version == 2
    assert p.write is not None
    assert p.write.merge is not None
    assert p.write.merge.mode == WriteMode.MERGE_ON_READ
    assert p.write.delete is not None
    assert p.write.delete.parquet is not None
    assert p.write.delete.parquet.compression_codec == "zstd"
    assert p.write.distribution_mode == DistributionMode.HASH
    assert p.read is not None
    assert p.read.split is not None
    assert p.read.split.size == 134217728


def test_package_reexports():
    """Verify __init__.py re-exports key symbols."""
    from application.domain.model.catalog.table_properties import (
        TableProperties as TP,
        WriteMode as WM,
    )

    assert TP is not None
    assert WM.COPY_ON_WRITE == "copy-on-write"
