"""GetTable use case definition."""

from application.port.inbound.catalog.get_table.input import GetTableInput
from application.port.inbound.catalog.get_table.output import GetTableOutput
from application.port.inbound.catalog.get_table.use_case import GetTableUseCase

__all__ = ["GetTableInput", "GetTableOutput", "GetTableUseCase"]
