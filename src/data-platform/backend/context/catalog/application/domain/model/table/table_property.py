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
    writes the default instead of removing the key. ``set_by_catalog`` is a key the catalog
    service writes itself; it is never modified.
    """

    key: str
    current_value: str | None
    default_value: str | None
    default_source: TablePropertyDefaultSource | None
    description: str | None
    custom: bool
    resettable: bool
    reset_writes_default: bool = False
    set_by_catalog: bool = False

    @model_validator(mode="after")
    def _a_written_default_exists(self) -> Self:
        if self.reset_writes_default and self.default_value is None:
            raise ValueError(f"{self.key}: a reset that writes the default needs a default")
        return self

    @property
    def modified(self) -> bool:
        """Return True when the table does not behave as its default says.

        A key set to something other than its default is modified, and so is a set key without
        a default (custom or not). An unset key is modified only when its default does not
        apply until written (``reset_writes_default``: a catalog default, which applies only at
        create, or a key Iceberg writes on create). A key the catalog service sets never is.
        """
        if self.set_by_catalog:
            return False
        if self.current_value is None:
            return self.reset_writes_default
        return self.default_value is None or self.current_value != self.default_value

    def reset_value(self) -> str | None:
        """Return the value a reset writes, or None when a reset removes the key."""
        return self.default_value if self.reset_writes_default else None
