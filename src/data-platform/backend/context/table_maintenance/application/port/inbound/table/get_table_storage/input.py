"""Define the GetTableStorageUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class GetTableStorageUseCaseInput(UseCaseInput):
    """Carry the request to get the storage of one table."""

    uuid: str
