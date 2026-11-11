"""Define the EnsureDefaultTableMaintenancePolicyUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EnsureDefaultTableMaintenancePolicyUseCaseOutput:
    """Describe the result."""

    created: bool
