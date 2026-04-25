"""Define the FieldChange value object."""

from __future__ import annotations

from dataclasses import dataclass

from core.base.value_object import ValueObject


@dataclass(frozen=True)
class FieldChange(ValueObject):
    """A record of a single field change with before/after values."""

    field: str
    old_value: str | None
    new_value: str | None
