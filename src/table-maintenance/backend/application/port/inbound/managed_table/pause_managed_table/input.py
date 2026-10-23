"""Define the PauseManagedTableUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PauseManagedTableUseCaseInput:
    """Carry the request to pause maintenance of a managed table."""

    uuid: str
