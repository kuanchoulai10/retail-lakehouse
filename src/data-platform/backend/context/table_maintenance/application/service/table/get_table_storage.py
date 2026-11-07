"""Define the GetTableStorageService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
)
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    OperationRunStatus,
)
from context.table_maintenance.application.port.inbound.table import (
    GetTableStorageUseCase,
    GetTableStorageUseCaseInput,
    GetTableStorageUseCaseOutput,
)
from context.table_maintenance.application.service.table.load_catalog_table import (
    load_catalog_table,
)
from context.table_maintenance.application.service.table.raise_not_in_catalog import (
    raise_not_in_catalog,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.port.outbound.table import (
        ReadTableMetadataGateway,
        TablesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_run import (
        TableMaintenanceRunsRepo,
    )

_WINDOW_DAYS = 30
_NO_CALLBACK_METRICS = {"completed_without_callback": 1}

_RECLAIMED_KEYS: dict[str, tuple[MaintenanceOperation, str]] = {
    "rewritten_data_files": (
        MaintenanceOperation.REWRITE_DATA_FILES,
        "rewritten_data_files_count",
    ),
    "added_data_files": (
        MaintenanceOperation.REWRITE_DATA_FILES,
        "added_data_files_count",
    ),
    "rewritten_bytes": (
        MaintenanceOperation.REWRITE_DATA_FILES,
        "rewritten_bytes_count",
    ),
    "rewritten_manifests": (
        MaintenanceOperation.REWRITE_MANIFESTS,
        "rewritten_manifests_count",
    ),
    "added_manifests": (
        MaintenanceOperation.REWRITE_MANIFESTS,
        "added_manifests_count",
    ),
    "expired_snapshots": (
        MaintenanceOperation.EXPIRE_SNAPSHOTS,
        "deleted_manifest_lists_count",
    ),
    "deleted_data_files": (
        MaintenanceOperation.EXPIRE_SNAPSHOTS,
        "deleted_data_files_count",
    ),
    "deleted_manifest_files": (
        MaintenanceOperation.EXPIRE_SNAPSHOTS,
        "deleted_manifest_files_count",
    ),
    "deleted_position_delete_files": (
        MaintenanceOperation.EXPIRE_SNAPSHOTS,
        "deleted_position_delete_files_count",
    ),
    "deleted_equality_delete_files": (
        MaintenanceOperation.EXPIRE_SNAPSHOTS,
        "deleted_equality_delete_files_count",
    ),
}


class GetTableStorageService(GetTableStorageUseCase):
    """Report what a table stores and what maintenance reclaimed in 30 days."""

    def __init__(
        self,
        tables_repo: TablesRepo,
        catalog_gateway: ReadTableMetadataGateway,
        runs_repo: TableMaintenanceRunsRepo,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repos, the catalog gateway and the clock."""
        self._tables_repo = tables_repo
        self._catalog_gateway = catalog_gateway
        self._runs_repo = runs_repo
        self._clock = clock

    def execute(
        self, request: GetTableStorageUseCaseInput
    ) -> GetTableStorageUseCaseOutput:
        """Measure the table and sum its recent reclaimed space, or raise NotFoundError."""
        table, ref = load_catalog_table(self._tables_repo, request.uuid)
        measure = self._catalog_gateway.measure_storage(ref)
        if measure is None or measure.table_uuid != table.id.value:
            raise_not_in_catalog(table)
        since = self._clock() - timedelta(days=_WINDOW_DAYS)
        reclaimed = dict.fromkeys(_RECLAIMED_KEYS, 0)
        without_metrics = 0
        for run in self._runs_repo.list_by_table_since(table.id, since):
            for op in run.operations:
                if op.status is not OperationRunStatus.SUCCEEDED:
                    continue
                if op.metrics == _NO_CALLBACK_METRICS:
                    without_metrics += 1
                    continue
                for name, (operation, key) in _RECLAIMED_KEYS.items():
                    if op.operation is operation:
                        reclaimed[name] += op.metrics.get(key, 0)
        return GetTableStorageUseCaseOutput(
            current_bytes=measure.current_bytes,
            current_files=measure.current_files,
            old_snapshot_bytes=max(0, measure.referenced_bytes - measure.current_bytes),
            old_snapshot_files=max(0, measure.referenced_files - measure.current_files),
            window_days=_WINDOW_DAYS,
            reclaimed=reclaimed,
            attempts_without_metrics=without_metrics,
        )
