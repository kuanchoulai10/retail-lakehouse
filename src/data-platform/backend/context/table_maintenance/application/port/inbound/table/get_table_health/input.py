"""Define the GetTableHealthUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class GetTableHealthUseCaseInput(UseCaseInput):
    """Carry the request to get the maintenance health of one table."""

    uuid: str
