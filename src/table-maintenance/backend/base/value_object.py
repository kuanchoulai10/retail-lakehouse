from __future__ import annotations

from abc import ABC
from dataclasses import dataclass


@dataclass(frozen=True)
class ValueObject(ABC):  # noqa: B024
    """An immutable, self-contained descriptor with no conceptual identity.

    Two ValueObjects are equal when all of their attributes are equal,
    regardless of where or when they were created. Because they carry no
    identity, they are freely shareable and safe to use as dict keys or
    set members.

    Examples: Money(amount, currency), Address(street, city, zip),
    DateRange(start, end).

    Rules:
        - Immutable: once created, attributes never change.
        - Equality by value: compared by all attributes, not by reference.
        - Side-effect free: methods return new instances rather than mutating.
        - Self-validating: invalid states are rejected at construction time.

    Usage::

        @dataclass(frozen=True)
        class Money(ValueObject):
            amount: int
            currency: str

    Subclasses must use @dataclass(frozen=True). Python enforces this:
    a non-frozen dataclass cannot inherit from a frozen one.
    """
