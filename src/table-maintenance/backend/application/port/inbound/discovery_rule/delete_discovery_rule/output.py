"""Define the DeleteDiscoveryRuleUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteDiscoveryRuleUseCaseOutput:
    """Signal completion; carries no data."""
