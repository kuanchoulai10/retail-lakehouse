"""Define the GetTableUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class GetTableUseCaseInput(UseCaseInput):
    """Carry the request to get one table."""

    uuid: str
