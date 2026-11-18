"""Define the EnsureDefaultTableMaintenancePolicyUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class EnsureDefaultTableMaintenancePolicyUseCaseOutput(UseCaseOutput):
    """Describe the result."""

    created: bool
