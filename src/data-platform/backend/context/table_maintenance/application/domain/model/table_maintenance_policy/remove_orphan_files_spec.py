"""Define the RemoveOrphanFilesSpec alias."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table_maintenance_policy.operation_spec import (
    OperationSpec,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.remove_orphan_files_options import (
    RemoveOrphanFilesOptions,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.remove_orphan_files_target import (
    RemoveOrphanFilesTarget,
)

RemoveOrphanFilesSpec = OperationSpec[RemoveOrphanFilesTarget, RemoveOrphanFilesOptions]
"""The ``remove_orphan_files`` block of a policy."""
