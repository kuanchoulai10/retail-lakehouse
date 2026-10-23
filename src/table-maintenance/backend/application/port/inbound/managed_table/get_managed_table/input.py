"""Define the GetManagedTableUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetManagedTableUseCaseInput:
    """Carry the request to get one managed table."""

    uuid: str
