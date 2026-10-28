"""Define the DeleteTableDiscoveryRuleUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteTableDiscoveryRuleUseCaseInput:
    """Carry the request to delete a discovery rule."""

    id: str
