"""Define the TableName value object."""

from __future__ import annotations

from pydantic import field_validator

from base import ValueObject


class TableName(ValueObject):
    """Locate an Iceberg table by catalog, namespace and table name.

    The namespace levels are joined with ``.``.
    """

    catalog: str
    namespace: str
    table: str

    @field_validator("table")
    @classmethod
    def _table_is_not_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("table name must not be empty")
        return value

    def qualified(self) -> str:
        """Return ``namespace.table``."""
        return f"{self.namespace}.{self.table}"

    def fully_qualified(self) -> str:
        """Return ``catalog.namespace.table``."""
        return f"{self.catalog}.{self.namespace}.{self.table}"
