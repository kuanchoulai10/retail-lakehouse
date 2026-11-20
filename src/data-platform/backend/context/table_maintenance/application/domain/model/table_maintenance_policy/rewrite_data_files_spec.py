"""Define the RewriteDataFilesSpec alias."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table_maintenance_policy.operation_spec import (
    OperationSpec,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_data_files_options import (
    RewriteDataFilesOptions,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_data_files_target import (
    RewriteDataFilesTarget,
)

RewriteDataFilesSpec = OperationSpec[RewriteDataFilesTarget, RewriteDataFilesOptions]
"""The ``rewrite_data_files`` block of a policy."""
