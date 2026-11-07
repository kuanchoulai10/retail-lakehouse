"""Define the GetTableHealthUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetTableHealthUseCaseInput:
    """Carry the request to get the maintenance health of one table."""

    uuid: str
