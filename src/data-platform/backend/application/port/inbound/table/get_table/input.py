"""Define the GetTableUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetTableUseCaseInput:
    """Carry the request to get one table."""

    uuid: str
