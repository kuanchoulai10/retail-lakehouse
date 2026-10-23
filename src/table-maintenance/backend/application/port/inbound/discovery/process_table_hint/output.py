"""Define the ProcessTableHintUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessTableHintUseCaseOutput:
    """Carry the result of the request to react to a catalog event hint about one table or namespace."""

    action: str
