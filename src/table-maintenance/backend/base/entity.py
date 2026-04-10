from __future__ import annotations

from abc import ABC

from pydantic import BaseModel


class Entity(ABC, BaseModel):
    """Object defined by a unique identity rather than its attributes."""

    id: str

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
