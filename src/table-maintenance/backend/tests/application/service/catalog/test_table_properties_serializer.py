"""Test table_properties_to_dict serializer."""

from __future__ import annotations

from application.domain.model.catalog.table_properties.delete_properties import (
    DeleteProperties,
)
from application.domain.model.catalog.table_properties.operation_properties import (
    OperationProperties,
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
from application.service.catalog.table_properties_serializer import (
    table_properties_to_dict,
)


def test_empty_properties():
    result = table_properties_to_dict(TableProperties())
    assert result == {}


def test_format_version():
    result = table_properties_to_dict(TableProperties(format_version=2))
    assert result == {"format-version": "2"}


def test_write_merge_mode():
    result = table_properties_to_dict(
        TableProperties(
            write=WriteProperties(
                merge=OperationProperties(mode=WriteMode.MERGE_ON_READ),
            ),
        )
    )
    assert result["write.merge.mode"] == "merge-on-read"


def test_write_delete_with_parquet():
    result = table_properties_to_dict(
        TableProperties(
            write=WriteProperties(
                delete=DeleteProperties(
                    mode=WriteMode.COPY_ON_WRITE,
                    format_default="parquet",
                    target_file_size_bytes=67108864,
                    parquet=ParquetProperties(compression_codec="zstd"),
                ),
            ),
        )
    )
    assert result["write.delete.mode"] == "copy-on-write"
    assert result["write.delete.format.default"] == "parquet"
    assert result["write.delete.target-file-size-bytes"] == "67108864"
    assert result["write.delete.parquet.compression-codec"] == "zstd"


def test_write_flags():
    result = table_properties_to_dict(
        TableProperties(
            write=WriteProperties(upsert_enabled=True, wap_enabled=False),
        )
    )
    assert result["write.upsert.enabled"] == "true"
    assert result["write.wap.enabled"] == "false"


def test_read_split():
    result = table_properties_to_dict(
        TableProperties(
            read=ReadProperties(split=SplitProperties(size=134217728, lookback=10)),
        )
    )
    assert result["read.split.planning.size"] == "134217728"
    assert result["read.split.planning.lookback"] == "10"


def test_skips_none_values():
    """None fields should not appear in the output dict."""
    result = table_properties_to_dict(
        TableProperties(
            write=WriteProperties(
                merge=OperationProperties(mode=WriteMode.MERGE_ON_READ),
            ),
        )
    )
    assert "write.merge.isolation-level" not in result
    assert "write.merge.distribution-mode" not in result


def test_roundtrip():
    """dict -> TableProperties -> dict should preserve all values."""
    from adapter.outbound.catalog.dict_to_table_properties import (
        dict_to_table_properties,
    )

    original = {
        "format-version": "2",
        "write.merge.mode": "merge-on-read",
        "write.delete.mode": "copy-on-write",
        "write.delete.parquet.compression-codec": "zstd",
        "write.distribution-mode": "hash",
        "write.format.default": "parquet",
        "write.parquet.compression-codec": "snappy",
        "write.target-file-size-bytes": "536870912",
        "write.upsert.enabled": "true",
        "read.split.planning.size": "134217728",
        "read.parquet.vectorization.enabled": "true",
    }
    props = dict_to_table_properties(original)
    result = table_properties_to_dict(props)
    assert result == original
