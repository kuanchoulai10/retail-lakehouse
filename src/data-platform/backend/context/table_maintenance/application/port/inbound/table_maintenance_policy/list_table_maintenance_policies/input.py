"""Define the ListTableMaintenancePoliciesUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListTableMaintenancePoliciesUseCaseInput:
    """Carry the request to list all table maintenance policies."""
