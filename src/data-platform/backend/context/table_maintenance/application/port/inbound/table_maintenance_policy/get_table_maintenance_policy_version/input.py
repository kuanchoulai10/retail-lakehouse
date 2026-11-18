"""Define the GetTableMaintenancePolicyVersionUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class GetTableMaintenancePolicyVersionUseCaseInput(UseCaseInput):
    """Carry the request to get one version of a table maintenance policy."""

    name: str
    version: int
