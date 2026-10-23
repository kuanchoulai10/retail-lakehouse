"""Define the DeleteDiscoveryRuleUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteDiscoveryRuleUseCaseInput:
    """Carry the request to delete a discovery rule."""

    id: str
