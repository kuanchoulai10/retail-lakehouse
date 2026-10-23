"""Define the TablePattern value object."""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase

from application.domain.model.managed_table.table_name import TableName
from base.value_object import ValueObject


@dataclass(frozen=True)
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
