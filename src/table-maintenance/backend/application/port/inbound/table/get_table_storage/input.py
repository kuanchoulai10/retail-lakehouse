"""Define the GetTableStorageUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetTableStorageUseCaseInput:
    """Carry the request to get the storage of one table."""

    uuid: str
