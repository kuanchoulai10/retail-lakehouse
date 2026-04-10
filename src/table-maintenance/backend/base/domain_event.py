from __future__ import annotations

from abc import ABC
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class DomainEvent(ABC, BaseModel, frozen=True):
    """Something that happened in the domain."""

    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
