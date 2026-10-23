"""Define the ListDiscoveryRulesUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListDiscoveryRulesUseCaseInput:
    """Carry the request to list all discovery rules."""
