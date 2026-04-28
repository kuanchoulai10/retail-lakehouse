"""Test dict_to_table_properties converter."""

from __future__ import annotations

from adapter.outbound.catalog.dict_to_table_properties import dict_to_table_properties
from application.domain.model.catalog.table_properties.distribution_mode import (
    DistributionMode,
)
from application.domain.model.catalog.table_properties.isolation_level import (
    IsolationLevel,
)
from application.domain.model.catalog.table_properties.write_mode import WriteMode


def test_empty_dict():
    result = dict_to_table_properties({})
    assert result.format_version is None
    assert result.write is None
    assert result.read is None


def test_format_version():
    result = dict_to_table_properties({"format-version": "2"})
    assert result.format_version == 2


def test_write_merge_mode():
    result = dict_to_table_properties({"write.merge.mode": "merge-on-read"})
    assert result.write is not None
    assert result.write.merge is not None
    assert result.write.merge.mode == WriteMode.MERGE_ON_READ


def test_write_update_mode():
    result = dict_to_table_properties({"write.update.mode": "copy-on-write"})
    assert result.write is not None
    assert result.write.update is not None
    assert result.write.update.mode == WriteMode.COPY_ON_WRITE


def test_write_delete_mode():
    result = dict_to_table_properties(
        {
            "write.delete.mode": "copy-on-write",
            "write.delete.isolation-level": "serializable",
            "write.delete.distribution-mode": "hash",
        }
    )
    assert result.write is not None
    assert result.write.delete is not None
    assert result.write.delete.mode == WriteMode.COPY_ON_WRITE
    assert result.write.delete.isolation_level == IsolationLevel.SERIALIZABLE
    assert result.write.delete.distribution_mode == DistributionMode.HASH


def test_write_delete_parquet():
    result = dict_to_table_properties(
        {
            "write.delete.parquet.compression-codec": "zstd",
            "write.delete.parquet.row-group-size-bytes": "134217728",
        }
    )
    assert result.write is not None
    assert result.write.delete is not None
    assert result.write.delete.parquet is not None
    assert result.write.delete.parquet.compression_codec == "zstd"
    assert result.write.delete.parquet.row_group_size_bytes == 134217728


def test_write_delete_format_and_size():
    result = dict_to_table_properties(
        {
            "write.delete.format.default": "parquet",
            "write.delete.target-file-size-bytes": "67108864",
        }
    )
    assert result.write is not None
    assert result.write.delete is not None
    assert result.write.delete.format_default == "parquet"
    assert result.write.delete.target_file_size_bytes == 67108864


def test_write_distribution_mode():
    result = dict_to_table_properties({"write.distribution-mode": "range"})
    assert result.write is not None
    assert result.write.distribution_mode == DistributionMode.RANGE


def test_write_format_default():
    result = dict_to_table_properties({"write.format.default": "parquet"})
    assert result.write is not None
    assert result.write.format is not None
    assert result.write.format.default == "parquet"


def test_write_parquet_settings():
    result = dict_to_table_properties(
        {
            "write.parquet.compression-codec": "snappy",
            "write.parquet.compression-level": "5",
            "write.parquet.row-group-size-bytes": "134217728",
            "write.parquet.page-size-bytes": "1048576",
            "write.parquet.dict-size-bytes": "2097152",
        }
    )
    assert result.write is not None
    assert result.write.parquet is not None
    assert result.write.parquet.compression_codec == "snappy"
    assert result.write.parquet.compression_level == 5
    assert result.write.parquet.row_group_size_bytes == 134217728
    assert result.write.parquet.page_size_bytes == 1048576
    assert result.write.parquet.dict_size_bytes == 2097152


def test_write_target_file_size():
    result = dict_to_table_properties({"write.target-file-size-bytes": "536870912"})
    assert result.write is not None
    assert result.write.target_file_size_bytes == 536870912


def test_write_manifest():
    result = dict_to_table_properties(
        {
            "write.manifest.target-size-bytes": "8388608",
            "write.manifest.min-merge-count": "4",
            "write.manifest.merge.enabled": "true",
        }
    )
    assert result.write is not None
    assert result.write.manifest is not None
    assert result.write.manifest.target_size_bytes == 8388608
    assert result.write.manifest.min_merge_count == 4
    assert result.write.manifest.merge_enabled is True


def test_write_metadata():
    result = dict_to_table_properties(
        {
            "write.metadata.compression-codec": "gzip",
            "write.metadata.delete-after-commit.enabled": "false",
            "write.metadata.previous-versions-max": "100",
        }
    )
    assert result.write is not None
    assert result.write.metadata is not None
    assert result.write.metadata.compression_codec == "gzip"
    assert result.write.metadata.delete_after_commit_enabled is False
    assert result.write.metadata.previous_versions_max == 100


def test_write_commit():
    result = dict_to_table_properties(
        {
            "write.commit.num-retries": "3",
            "write.commit.retry.min-wait-ms": "100",
            "write.commit.retry.max-wait-ms": "60000",
            "write.commit.retry.total-timeout-ms": "600000",
        }
    )
    assert result.write is not None
    assert result.write.commit is not None
    assert result.write.commit.num_retries == 3
    assert result.write.commit.retry_min_wait_ms == 100
    assert result.write.commit.retry_max_wait_ms == 60000
    assert result.write.commit.total_retry_time_ms == 600000


def test_write_metrics():
    result = dict_to_table_properties({"write.metrics.mode": "truncate(16)"})
    assert result.write is not None
    assert result.write.metrics is not None
    assert result.write.metrics.default_mode == "truncate(16)"


def test_write_flags():
    result = dict_to_table_properties(
        {
            "write.upsert.enabled": "true",
            "write.wap.enabled": "false",
            "write.object-storage.enabled": "true",
        }
    )
    assert result.write is not None
    assert result.write.upsert_enabled is True
    assert result.write.wap_enabled is False
    assert result.write.object_storage_enabled is True


def test_read_split():
    result = dict_to_table_properties(
        {
            "read.split.planning.size": "134217728",
            "read.split.planning.lookback": "10",
            "read.split.planning.open-file-cost": "4194304",
        }
    )
    assert result.read is not None
    assert result.read.split is not None
    assert result.read.split.size == 134217728
    assert result.read.split.lookback == 10
    assert result.read.split.open_file_cost == 4194304


def test_read_parquet():
    result = dict_to_table_properties(
        {
            "read.parquet.vectorization.enabled": "true",
            "read.parquet.batch-size": "128",
        }
    )
    assert result.read is not None
    assert result.read.parquet is not None
    assert result.read.parquet.vectorization_enabled is True
    assert result.read.parquet.batch_size == 128


def test_read_orc():
    result = dict_to_table_properties(
        {
            "read.orc.vectorization.enabled": "false",
            "read.orc.batch-size": "256",
        }
    )
    assert result.read is not None
    assert result.read.orc is not None
    assert result.read.orc.vectorization_enabled is False
    assert result.read.orc.batch_size == 256


def test_none_groups_when_no_keys_present():
    """Groups that have zero keys should be None, not empty VOs."""
    result = dict_to_table_properties({"format-version": "2"})
    assert result.write is None
    assert result.read is None


def test_nested_none_groups():
    """Sub-groups that have zero keys should be None."""
    result = dict_to_table_properties({"write.merge.mode": "merge-on-read"})
    assert result.write is not None
    assert result.write.update is None
    assert result.write.delete is None
    assert result.write.parquet is None
