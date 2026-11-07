"""Define the ProcessTableHintUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessTableHintUseCaseInput:
    """Carry the request to react to a catalog event hint about one table or namespace."""

    catalog: str
    namespace: str
    table: str | None
    event_type: str
