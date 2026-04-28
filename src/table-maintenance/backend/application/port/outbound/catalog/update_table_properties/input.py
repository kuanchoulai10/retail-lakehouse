"""Define the UpdateTablePropertiesInput value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class UpdateTablePropertiesInput(ValueObject):
    """Primitive-only input for updating table properties via the catalog.

    Uses only primitive types so adapter implementations need zero domain imports.
    """

    namespace: str
    table: str
    updates: dict[str, str]
    removals: list[str]
