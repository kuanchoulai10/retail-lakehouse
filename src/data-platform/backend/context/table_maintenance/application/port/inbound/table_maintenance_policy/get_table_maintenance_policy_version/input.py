"""Define the GetTableMaintenancePolicyVersionUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetTableMaintenancePolicyVersionUseCaseInput:
    """Carry the request to get one version of a table maintenance policy."""

    name: str
    version: int
