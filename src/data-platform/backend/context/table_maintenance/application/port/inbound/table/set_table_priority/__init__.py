"""Set how urgently a table's maintenance is scheduled."""

from context.table_maintenance.application.port.inbound.table.set_table_priority.input import (
    SetTablePriorityUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table.set_table_priority.output import (
    SetTablePriorityUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table.set_table_priority.use_case import (
    SetTablePriorityUseCase,
)

__all__ = [
    "SetTablePriorityUseCase",
    "SetTablePriorityUseCaseInput",
    "SetTablePriorityUseCaseOutput",
]
