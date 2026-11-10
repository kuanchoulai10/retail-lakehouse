"""Define the TablePattern value object."""

from __future__ import annotations

from fnmatch import fnmatchcase
from typing import TYPE_CHECKING

from base import ValueObject

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table import TableName


class TablePattern(ValueObject):
    """Match tables by case-sensitive glob on catalog, namespace and table."""

    catalog: str = "*"
    namespace: str = "*"
    table: str = "*"

    def matches(self, name: TableName) -> bool:
        """Return whether every part of the name matches its glob."""
        return (
            fnmatchcase(name.catalog, self.catalog)
            and fnmatchcase(name.namespace, self.namespace)
            and fnmatchcase(name.table, self.table)
        )
