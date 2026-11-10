"""Define the Pydantic DomainEvent base class."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from base import enforce_max_depth


def _now() -> datetime:
    return datetime.now(UTC)


class DomainEvent(BaseModel):
    """A record of something meaningful that occurred in the domain.

    Named in past tense (OrderPlaced), frozen and strict. Every event
    carries ``occurred_at``, which defaults to the current UTC time.

    Usage::

        class OrderPlaced(DomainEvent):
            order_id: str
            total: int
    """

    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        validate_by_name=True,
        validate_by_alias=True,
    )

    occurred_at: datetime = Field(default_factory=_now)

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """Enforce flat hierarchy: concrete events extend DomainEvent directly (max depth 1)."""
        super().__pydantic_init_subclass__(**kwargs)
        enforce_max_depth(cls, DomainEvent, 1)
