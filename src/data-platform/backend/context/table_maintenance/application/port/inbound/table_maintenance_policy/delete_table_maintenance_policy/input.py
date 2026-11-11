"""Define the DeleteTableMaintenancePolicyUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteTableMaintenancePolicyUseCaseInput:
    """Carry the request to delete a table maintenance policy and its versions."""

    name: str
