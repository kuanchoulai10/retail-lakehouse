"""Define the TableReference value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class TableReference(ValueObject):
    """An immutable reference to a table within a catalog."""

    catalog: str
    table: str
