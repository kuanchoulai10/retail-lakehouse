"""Define the ListTableDiscoveryRulesUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListTableDiscoveryRulesUseCaseInput:
    """Carry the request to list all discovery rules."""
