from __future__ import annotations

from abc import ABC
from dataclasses import dataclass


@dataclass(eq=False)
class Entity(ABC):
    """Object defined by a unique identity rather than its attributes.

    Subclasses should use @dataclass(eq=False) to preserve identity-based equality.
    """

    id: str  # noqa: A003

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
