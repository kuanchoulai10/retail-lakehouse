"""ListTables use case definition."""

from core.application.port.inbound.catalog.list_tables.input import ListTablesInput
from core.application.port.inbound.catalog.list_tables.output import ListTablesOutput
from core.application.port.inbound.catalog.list_tables.use_case import ListTablesUseCase

__all__ = ["ListTablesInput", "ListTablesOutput", "ListTablesUseCase"]
