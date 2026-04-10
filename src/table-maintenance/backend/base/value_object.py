from __future__ import annotations

from abc import ABC


class ValueObject(ABC):  # noqa: B024
    """Immutable object defined by its attributes, not by identity.

    Subclasses should use @dataclass(frozen=True) to enforce immutability.
    """
