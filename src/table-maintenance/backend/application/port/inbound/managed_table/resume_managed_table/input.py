"""Define the ResumeManagedTableUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResumeManagedTableUseCaseInput:
    """Carry the request to resume maintenance of a managed table."""

    uuid: str
