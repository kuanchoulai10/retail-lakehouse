"""Define the ReadOrcProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class ReadOrcProperties(ValueObject):
    """ORC read optimization properties."""

    vectorization_enabled: bool | None = None
    batch_size: int | None = None
