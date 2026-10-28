"""Table domain vocabulary."""

from __future__ import annotations

from application.domain.model.table.invalid_table_transition import (
    InvalidTableTransition,
)
from application.domain.model.table.operation_state import OperationState
from application.domain.model.table.table import Table
from application.domain.model.table.table_change import TableChange
from application.domain.model.table.table_id import TableId
from application.domain.model.table.table_name import TableName
from application.domain.model.table.table_selection import TableSelection
from application.domain.model.table.table_status import TableStatus

__all__ = [
    "InvalidTableTransition",
    "OperationState",
    "Table",
    "TableChange",
    "TableId",
    "TableName",
    "TableSelection",
    "TableStatus",
]
