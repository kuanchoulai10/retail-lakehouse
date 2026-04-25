"""Define the EntityId base class."""

from __future__ import annotations

from dataclasses import dataclass

from core.base.value_object import ValueObject


@dataclass(frozen=True)
class EntityId(ValueObject):
    """A typed identifier for an Entity.

    Wraps a raw string value in a distinct type so that IDs belonging to
    different Entity kinds cannot be accidentally mixed up.

    Subclass per Entity type for compile-time safety::

        @dataclass(frozen=True)
        class OrderId(EntityId):
            pass

        @dataclass(frozen=True)
        class UserId(EntityId):
            pass

    ``OrderId("1") != UserId("1")`` — same value, different types.
    """

    value: str

    def __str__(self) -> str:
        """Return the raw identifier string."""
        return self.value
