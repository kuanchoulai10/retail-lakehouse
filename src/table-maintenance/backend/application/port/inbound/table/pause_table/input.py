"""Define the PauseTableUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PauseTableUseCaseInput:
    """Carry the request to pause maintenance of a table."""

    uuid: str
