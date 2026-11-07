"""Define the DomainEvent base class."""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from datetime import UTC, datetime

from base._inheritance_guard import enforce_max_depth


@dataclass(frozen=True)
class DomainEvent(ABC):  # noqa: B024
    """A record of something meaningful that occurred in the domain.

    DomainEvents are named in past tense (OrderPlaced, PaymentReceived)
    and capture the facts of what happened, not commands for what should
    happen next. They are immutable: once an event has occurred, it
    cannot be changed.

    Every event carries an ``occurred_at`` timestamp that is automatically
    set to the current UTC time at construction.

    Examples: OrderPlaced(order_id), InventoryAdjusted(sku, delta),
    SnapshotExpired(table, expired_count).

    Rules:
        - Immutable: events describe the past and cannot be altered.
        - Named in past tense: describes what already happened.
        - Self-contained: carries all data needed to understand the event.
        - Timestamped: ``occurred_at`` is set automatically.

    Usage::

        @dataclass(frozen=True)
        class OrderPlaced(DomainEvent):
            order_id: str
            total: int

    Subclasses must use @dataclass(frozen=True) to enforce immutability.
    """

    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(UTC), kw_only=True
    )

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Enforce flat hierarchy: concrete events extend DomainEvent directly (max depth 1)."""
        super().__init_subclass__(**kwargs)
        enforce_max_depth(cls, DomainEvent, 1)
