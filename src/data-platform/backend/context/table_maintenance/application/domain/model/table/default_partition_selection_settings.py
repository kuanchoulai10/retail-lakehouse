"""Define the partition selection settings a platform runs with unless it is told otherwise."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table.partition_selection_settings import (
    PartitionSelectionSettings,
)

DEFAULT_PARTITION_SELECTION_SETTINGS = PartitionSelectionSettings.platform_default()
