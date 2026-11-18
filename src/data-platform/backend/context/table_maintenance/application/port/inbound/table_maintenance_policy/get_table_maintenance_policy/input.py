"""Define the GetTableMaintenancePolicyUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class GetTableMaintenancePolicyUseCaseInput(UseCaseInput):
    """Carry the request to get the current version of a table maintenance policy."""

    name: str
