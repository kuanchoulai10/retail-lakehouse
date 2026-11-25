"""Define the RemoveOrphanFilesJobContent value object."""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, Field

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
from context.table_maintenance.application.domain.model.table_maintenance_policy import RemoveOrphanFilesOptions


class RemoveOrphanFilesJobContent(ValueObject):
    """Describe what one orphan file removal does: files no snapshot holds, written before ``older_than``."""

    operation: Literal[MaintenanceOperation.REMOVE_ORPHAN_FILES] = MaintenanceOperation.REMOVE_ORPHAN_FILES
    older_than: AwareDatetime
    options: RemoveOrphanFilesOptions = Field(default_factory=RemoveOrphanFilesOptions)
