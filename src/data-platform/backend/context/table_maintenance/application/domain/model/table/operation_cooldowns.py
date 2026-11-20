"""Define the OperationCooldowns value object."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    NonNegativeDuration,
    PositiveDuration,
)
from context.table_maintenance.application.domain.model.table.default_failure_backoff_cap import (
    DEFAULT_FAILURE_BACKOFF_CAP,
)

if TYPE_CHECKING:
    from typing import Self


class OperationCooldowns(ValueObject):
    """Hold the platform's least time between two attempts of each operation on one table.

    Compaction, manifest rewriting and snapshot expiry are held back by their cooldown after an
    attempt; ``remove_orphan_files`` is the interval at which orphan files are removed, since they
    have no target the platform can measure. ``failure_backoff_cap`` is where the doubling of a
    failing operation's cooldown stops.
    """

    rewrite_data_files: NonNegativeDuration
    rewrite_manifests: NonNegativeDuration
    expire_snapshots: NonNegativeDuration
    remove_orphan_files: PositiveDuration
    failure_backoff_cap: PositiveDuration

    @classmethod
    def platform_default(cls) -> Self:
        """Return the cooldowns a platform runs with unless it is told otherwise."""
        return cls(
            rewrite_data_files=timedelta(hours=1),
            rewrite_manifests=timedelta(hours=6),
            expire_snapshots=timedelta(hours=6),
            remove_orphan_files=timedelta(days=7),
            failure_backoff_cap=DEFAULT_FAILURE_BACKOFF_CAP,
        )

    def for_operation(self, operation: MaintenanceOperation) -> timedelta:
        """Return the cooldown of ``operation``."""
        match operation:
            case MaintenanceOperation.REWRITE_DATA_FILES:
                return self.rewrite_data_files
            case MaintenanceOperation.REWRITE_MANIFESTS:
                return self.rewrite_manifests
            case MaintenanceOperation.EXPIRE_SNAPSHOTS:
                return self.expire_snapshots
            case MaintenanceOperation.REMOVE_ORPHAN_FILES:
                return self.remove_orphan_files
