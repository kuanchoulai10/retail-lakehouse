"""Generic table use case implementations."""

from __future__ import annotations

from context.catalog.application.service.generic_table.create_generic_table import CreateGenericTableService
from context.catalog.application.service.generic_table.delete_generic_table import DeleteGenericTableService
from context.catalog.application.service.generic_table.generic_table_id_from_parts import (
    generic_table_id_from_parts,
)
from context.catalog.application.service.generic_table.generic_table_output_fields import (
    generic_table_output_fields,
)
from context.catalog.application.service.generic_table.get_generic_table import GetGenericTableService
from context.catalog.application.service.generic_table.list_generic_tables import ListGenericTablesService

__all__ = [
    "CreateGenericTableService",
    "DeleteGenericTableService",
    "GetGenericTableService",
    "ListGenericTablesService",
    "generic_table_id_from_parts",
    "generic_table_output_fields",
]
