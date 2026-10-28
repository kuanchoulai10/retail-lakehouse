"""Define the ResumeTableUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResumeTableUseCaseInput:
    """Carry the request to resume maintenance of a table."""

    uuid: str
