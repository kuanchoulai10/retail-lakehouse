"""Define the ExpireSnapshotsJobContent value object."""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, Field, PositiveInt

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
from context.table_maintenance.application.domain.model.table_maintenance_policy import ExpireSnapshotsOptions


class ExpireSnapshotsJobContent(ValueObject):
    """Describe what one snapshot expiry does: which snapshots may go and how many always stay.

    Snapshots committed before ``older_than`` expire, except the newest ``retain_last``; both come
    from the policy's target, else the table's properties, else Iceberg's defaults.
    """

    operation: Literal[MaintenanceOperation.EXPIRE_SNAPSHOTS] = MaintenanceOperation.EXPIRE_SNAPSHOTS
    older_than: AwareDatetime
    retain_last: PositiveInt
    options: ExpireSnapshotsOptions = Field(default_factory=ExpireSnapshotsOptions)
