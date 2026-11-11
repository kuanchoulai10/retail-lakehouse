"""Define the GetTableMaintenancePolicyUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetTableMaintenancePolicyUseCaseInput:
    """Carry the request to get the current version of a table maintenance policy."""

    name: str
