"""Define the EnsureDefaultTableMaintenancePolicyUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EnsureDefaultTableMaintenancePolicyUseCaseInput:
    """Carry the request to create the default table maintenance policy when it is missing."""
