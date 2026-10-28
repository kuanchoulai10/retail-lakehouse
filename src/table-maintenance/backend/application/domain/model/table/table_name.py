"""Define the TableName value object."""

from __future__ import annotations

from dataclasses import dataclass

from base import ValueObject


@dataclass(frozen=True)
class TableName(ValueObject):
    """Locate an Iceberg table by catalog, namespace and table name.

    The namespace levels are joined with ``.``.
    """

    catalog: str
    namespace: str
    table: str

    def __post_init__(self) -> None:
        """Reject an empty table name."""
        if not self.table:
            raise ValueError("table name must not be empty")

    def qualified(self) -> str:
        """Return ``namespace.table``."""
        return f"{self.namespace}.{self.table}"

    def fully_qualified(self) -> str:
        """Return ``catalog.namespace.table``."""
        return f"{self.catalog}.{self.namespace}.{self.table}"
