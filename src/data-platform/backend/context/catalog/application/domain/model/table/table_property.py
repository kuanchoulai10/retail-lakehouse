"""Define the TableProperty value object."""

from __future__ import annotations

from typing import Self

from pydantic import model_validator

from base import ValueObject
from context.catalog.application.domain.model.table.table_property_default_source import (
    TablePropertyDefaultSource,
)


class TableProperty(ValueObject):
    """One property of a table next to its default: what the table holds and what a new table would.

    ``current_value`` is None when the table does not set the key. ``default_value`` is None
    when there is no default (a custom key, or a known key Iceberg leaves to the engine).
    ``custom`` is a key the catalogue does not know. ``reset_writes_default`` marks a key a new
    table holds explicitly (a catalog default, or a key Iceberg writes on create), so a reset
    writes the default instead of removing the key.
    """

    key: str
    current_value: str | None
    default_value: str | None
    default_source: TablePropertyDefaultSource | None
    description: str | None
    custom: bool
    resettable: bool
    reset_writes_default: bool = False

    @model_validator(mode="after")
    def _a_written_default_exists(self) -> Self:
        if self.reset_writes_default and self.default_value is None:
            raise ValueError(f"{self.key}: a reset that writes the default needs a default")
        return self

    @property
    def modified(self) -> bool:
        """Return True when the table sets the key to something other than its default, or sets a custom key."""
        if self.current_value is None:
            return False
        return self.custom or self.current_value != self.default_value

    def reset_value(self) -> str | None:
        """Return the value a reset writes, or None when a reset removes the key."""
        return self.default_value if self.reset_writes_default else None
