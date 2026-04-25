"""GetTable use case definition."""

from core.application.port.inbound.catalog.get_table.input import GetTableInput
from core.application.port.inbound.catalog.get_table.output import GetTableOutput
from core.application.port.inbound.catalog.get_table.use_case import GetTableUseCase

__all__ = ["GetTableInput", "GetTableOutput", "GetTableUseCase"]
