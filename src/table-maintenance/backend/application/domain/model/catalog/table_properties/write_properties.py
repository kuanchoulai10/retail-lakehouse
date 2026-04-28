"""Define the WriteProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject
from application.domain.model.catalog.table_properties.commit_properties import (
    CommitProperties,
)
from application.domain.model.catalog.table_properties.delete_properties import (
    DeleteProperties,
)
from application.domain.model.catalog.table_properties.distribution_mode import (
    DistributionMode,
)
from application.domain.model.catalog.table_properties.format_properties import (
    FormatProperties,
)
from application.domain.model.catalog.table_properties.manifest_properties import (
    ManifestProperties,
)
from application.domain.model.catalog.table_properties.metadata_properties import (
    MetadataProperties,
)
from application.domain.model.catalog.table_properties.metrics_properties import (
    MetricsProperties,
)
from application.domain.model.catalog.table_properties.operation_properties import (
    OperationProperties,
)
from application.domain.model.catalog.table_properties.parquet_properties import (
    ParquetProperties,
)


@dataclass(frozen=True)
class WriteProperties(ValueObject):
    """All write-related table properties."""

    merge: OperationProperties | None = None
    update: OperationProperties | None = None
    delete: DeleteProperties | None = None
    distribution_mode: DistributionMode | None = None
    format: FormatProperties | None = None
    parquet: ParquetProperties | None = None
    target_file_size_bytes: int | None = None
    manifest: ManifestProperties | None = None
    metadata: MetadataProperties | None = None
    commit: CommitProperties | None = None
    metrics: MetricsProperties | None = None
    upsert_enabled: bool | None = None
    wap_enabled: bool | None = None
    object_storage_enabled: bool | None = None
