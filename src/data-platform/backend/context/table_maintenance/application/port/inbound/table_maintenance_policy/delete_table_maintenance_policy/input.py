"""Define the DeleteTableMaintenancePolicyUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class DeleteTableMaintenancePolicyUseCaseInput(UseCaseInput):
    """Carry the request to delete a table maintenance policy and its versions."""

    name: str
