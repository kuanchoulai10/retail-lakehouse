"""Define the ResolveApplicableTableMaintenancePolicyUseCaseOutput."""

from __future__ import annotations

from typing import Any

from base import UseCaseOutput


class ResolveApplicableTableMaintenancePolicyUseCaseOutput(UseCaseOutput):
    """Carry the outcome of the request."""

    policy_name: str
    version: int
    content: dict[str, Any]
    target: dict[str, Any] | None
