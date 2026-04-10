from __future__ import annotations

from abc import ABC
from dataclasses import dataclass


@dataclass(frozen=True)
class ValueObject(ABC):  # noqa: B024
    """Immutable object defined by its attributes, not by identity.

    Subclasses must use @dataclass(frozen=True). Python enforces this:
    a non-frozen dataclass cannot inherit from a frozen one.
    """
