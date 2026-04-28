"""Define the FormatProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class FormatProperties(ValueObject):
    """Default file format properties."""

    default: str | None = None
