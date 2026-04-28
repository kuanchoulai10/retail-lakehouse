"""Catalog use case definitions."""

from application.port.inbound.catalog.get_table import (
    GetTableInput,
    GetTableOutput,
    GetTableUseCase,
)
from application.port.inbound.catalog.list_branches import (
    ListBranchesInput,
    ListBranchesOutput,
    ListBranchesUseCase,
)
from application.port.inbound.catalog.list_namespaces import (
    ListNamespacesInput,
    ListNamespacesOutput,
    ListNamespacesUseCase,
)
from application.port.inbound.catalog.list_snapshots import (
    ListSnapshotsInput,
    ListSnapshotsOutput,
    ListSnapshotsUseCase,
)
from application.port.inbound.catalog.list_tables import (
    ListTablesInput,
    ListTablesOutput,
    ListTablesUseCase,
)
from application.port.inbound.catalog.list_tags import (
    ListTagsInput,
    ListTagsOutput,
    ListTagsUseCase,
)
from application.port.inbound.catalog.update_table_properties import (
    UpdateTablePropertiesInput,
    UpdateTablePropertiesOutput,
    UpdateTablePropertiesUseCase,
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
    "UpdateTablePropertiesInput",
    "UpdateTablePropertiesOutput",
    "UpdateTablePropertiesUseCase",
]
