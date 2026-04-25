"""Catalog use case definitions."""

from core.application.port.inbound.catalog.get_table import (
    GetTableInput,
    GetTableOutput,
    GetTableUseCase,
)
from core.application.port.inbound.catalog.list_branches import (
    ListBranchesInput,
    ListBranchesOutput,
    ListBranchesUseCase,
)
from core.application.port.inbound.catalog.list_namespaces import (
    ListNamespacesInput,
    ListNamespacesOutput,
    ListNamespacesUseCase,
)
from core.application.port.inbound.catalog.list_snapshots import (
    ListSnapshotsInput,
    ListSnapshotsOutput,
    ListSnapshotsUseCase,
)
from core.application.port.inbound.catalog.list_tables import (
    ListTablesInput,
    ListTablesOutput,
    ListTablesUseCase,
)
from core.application.port.inbound.catalog.list_tags import (
    ListTagsInput,
    ListTagsOutput,
    ListTagsUseCase,
)

__all__ = [
    "GetTableInput",
    "GetTableOutput",
    "GetTableUseCase",
    "ListBranchesInput",
    "ListBranchesOutput",
    "ListBranchesUseCase",
    "ListNamespacesInput",
    "ListNamespacesOutput",
    "ListNamespacesUseCase",
    "ListSnapshotsInput",
    "ListSnapshotsOutput",
    "ListSnapshotsUseCase",
    "ListTablesInput",
    "ListTablesOutput",
    "ListTablesUseCase",
    "ListTagsInput",
    "ListTagsOutput",
    "ListTagsUseCase",
]
