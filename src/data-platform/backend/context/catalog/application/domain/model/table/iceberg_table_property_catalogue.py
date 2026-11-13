"""Define the iceberg_table_property_catalogue function: the known table properties of the Iceberg the platform runs."""

from __future__ import annotations

from context.catalog.application.domain.model.table.table_property_catalogue import (
    TablePropertyCatalogue,
)
from context.catalog.application.domain.model.table.table_property_definition import (
    TablePropertyDefinition as Known,
)

# The Iceberg of the maintenance Spark runtime (``GLAC_SPARK__ICEBERG_VERSION``, wave 25) and of
# Polaris 1.8.0. The defaults are the ``*_DEFAULT`` constants of ``org.apache.iceberg.TableProperties``
# and ``TableMetadata.DEFAULT_TABLE_FORMAT_VERSION`` at tag ``apache-iceberg-1.10.1``. ``created-at`` is not
# Iceberg's: Polaris 1.8.0 writes it on every create (``IcebergCatalogHandler``) and nothing reads it.
_ICEBERG_VERSION = "1.10.1"

_CATALOGUE = TablePropertyCatalogue(
    iceberg_version=_ICEBERG_VERSION,
    definitions=(
        Known(
            key="format-version",
            iceberg_default="2",
            description="Table format version; fixed at create and only ever upgraded, never removed.",
            resettable=False,
        ),
        Known(key="write.format.default", iceberg_default="parquet", description="File format of new data files."),
        Known(
            key="write.target-file-size-bytes",
            iceberg_default="536870912",
            description="Target size of a data file in bytes (512 MiB); compaction aims for it too.",
        ),
        Known(
            key="write.delete.target-file-size-bytes",
            iceberg_default="67108864",
            description="Target size of a delete file in bytes (64 MiB).",
        ),
        Known(
            key="write.distribution-mode",
            iceberg_default=None,
            description="How writes are distributed across tasks (none, hash or range); the engine decides when unset.",
        ),
        Known(
            key="write.delete.mode",
            iceberg_default="copy-on-write",
            description="Row-level delete strategy: copy-on-write or merge-on-read.",
        ),
        Known(
            key="write.update.mode",
            iceberg_default="copy-on-write",
            description="Row-level update strategy: copy-on-write or merge-on-read.",
        ),
        Known(
            key="write.merge.mode",
            iceberg_default="copy-on-write",
            description="MERGE INTO strategy: copy-on-write or merge-on-read.",
        ),
        Known(
            key="write.parquet.compression-codec",
            iceberg_default="zstd",
            description="Parquet compression codec; Iceberg writes zstd on every new table, an absent key means gzip.",
            written_on_create=True,
        ),
        Known(
            key="write.parquet.compression-level",
            iceberg_default=None,
            description="Parquet compression level; the codec's own default when unset.",
        ),
        Known(
            key="write.parquet.row-group-size-bytes",
            iceberg_default="134217728",
            description="Parquet row group size in bytes (128 MiB).",
        ),
        Known(
            key="write.parquet.page-size-bytes",
            iceberg_default="1048576",
            description="Parquet page size in bytes (1 MiB).",
        ),
        Known(
            key="write.parquet.dict-size-bytes",
            iceberg_default="2097152",
            description="Parquet dictionary page size in bytes (2 MiB).",
        ),
        Known(key="write.avro.compression-codec", iceberg_default="gzip", description="Avro compression codec."),
        Known(key="write.orc.compression-codec", iceberg_default="zlib", description="ORC compression codec."),
        Known(
            key="write.metadata.compression-codec",
            iceberg_default="none",
            description="Metadata file compression codec: none or gzip.",
        ),
        Known(
            key="write.metadata.delete-after-commit.enabled",
            iceberg_default="false",
            description="Delete the oldest tracked metadata files after each commit.",
        ),
        Known(
            key="write.metadata.previous-versions-max",
            iceberg_default="100",
            description="How many previous metadata files to track before deleting them after commit.",
        ),
        Known(
            key="write.metadata.metrics.default",
            iceberg_default="truncate(16)",
            description="Default column metrics mode: none, counts, truncate(length) or full.",
        ),
        Known(
            key="write.metadata.metrics.max-inferred-column-defaults",
            iceberg_default="100",
            description="How many columns get metrics by default.",
        ),
        Known(
            key="write.object-storage.enabled",
            iceberg_default="false",
            description="Spread data file paths with a hash prefix, for object stores.",
        ),
        Known(
            key="write.object-storage.partitioned-paths",
            iceberg_default="true",
            description="Keep partition values in object storage file paths.",
        ),
        Known(
            key="write.data.path",
            iceberg_default=None,
            description="Where new data files go; the table location's data folder when unset.",
        ),
        Known(
            key="write.metadata.path",
            iceberg_default=None,
            description="Where new metadata files go; the table location's metadata folder when unset.",
        ),
        Known(
            key="write.summary.partition-limit",
            iceberg_default="0",
            description="Changed partitions up to which a snapshot summary lists per-partition stats.",
        ),
        Known(
            key="write.wap.enabled",
            iceberg_default="false",
            description="Write-audit-publish: stage writes in snapshots that are not yet current.",
        ),
        Known(
            key="write.spark.fanout.enabled",
            iceberg_default="false",
            description="Let Spark write partitioned data without sorting it first.",
        ),
        Known(
            key="commit.retry.num-retries",
            iceberg_default="4",
            description="How many times a failed commit is retried.",
        ),
        Known(
            key="commit.retry.min-wait-ms",
            iceberg_default="100",
            description="Shortest wait before retrying a commit, in milliseconds.",
        ),
        Known(
            key="commit.retry.max-wait-ms",
            iceberg_default="60000",
            description="Longest wait before retrying a commit, in milliseconds (1 minute).",
        ),
        Known(
            key="commit.retry.total-timeout-ms",
            iceberg_default="1800000",
            description="Total time to keep retrying a commit, in milliseconds (30 minutes).",
        ),
        Known(
            key="commit.status-check.num-retries",
            iceberg_default="3",
            description="How many times an unknown commit outcome is checked.",
        ),
        Known(
            key="commit.status-check.min-wait-ms",
            iceberg_default="1000",
            description="Shortest wait between commit status checks, in milliseconds.",
        ),
        Known(
            key="commit.status-check.max-wait-ms",
            iceberg_default="60000",
            description="Longest wait between commit status checks, in milliseconds (1 minute).",
        ),
        Known(
            key="commit.status-check.total-timeout-ms",
            iceberg_default="1800000",
            description="Total time to keep checking a commit's status, in milliseconds (30 minutes).",
        ),
        Known(
            key="commit.manifest.target-size-bytes",
            iceberg_default="8388608",
            description="Target size of a merged manifest file in bytes (8 MiB).",
        ),
        Known(
            key="commit.manifest.min-count-to-merge",
            iceberg_default="100",
            description="Manifests a commit accumulates before it merges them.",
        ),
        Known(
            key="commit.manifest-merge.enabled",
            iceberg_default="true",
            description="Merge manifests automatically on append commits.",
        ),
        Known(
            key="history.expire.max-snapshot-age-ms",
            iceberg_default="432000000",
            description="Age in milliseconds after which expiry removes a snapshot (5 days).",
        ),
        Known(
            key="history.expire.min-snapshots-to-keep",
            iceberg_default="1",
            description="Snapshots expiry always keeps, however old.",
        ),
        Known(
            key="history.expire.max-ref-age-ms",
            iceberg_default="9223372036854775807",
            description="Age in milliseconds after which expiry removes a branch or tag (never by default).",
        ),
        Known(
            key="read.split.target-size",
            iceberg_default="134217728",
            description="Target size of a read split in bytes (128 MiB).",
        ),
        Known(
            key="read.split.metadata-target-size",
            iceberg_default="33554432",
            description="Target size of a metadata table read split in bytes (32 MiB).",
        ),
        Known(
            key="read.split.planning-lookback",
            iceberg_default="10",
            description="Bins considered when combining files into read splits.",
        ),
        Known(
            key="read.split.open-file-cost",
            iceberg_default="4194304",
            description="Estimated cost of opening a file when planning splits, in bytes (4 MiB).",
        ),
        Known(
            key="read.split.adaptive-size.enabled",
            iceberg_default="true",
            description="Let the engine adapt the split size to the table's size.",
        ),
        Known(
            key="gc.enabled",
            iceberg_default="true",
            description=(
                "Allow snapshot expiry and orphan file removal to delete files; "
                "not reset by Reset to default, edit it deliberately."
            ),
            resettable=False,
        ),
        Known(
            key="created-at",
            iceberg_default=None,
            description="When Polaris created the table; written by Polaris.",
            resettable=False,
            set_by_catalog=True,
        ),
    ),
)


def iceberg_table_property_catalogue() -> TablePropertyCatalogue:
    """Return the known table properties with the defaults of the Iceberg version the platform runs."""
    return _CATALOGUE
