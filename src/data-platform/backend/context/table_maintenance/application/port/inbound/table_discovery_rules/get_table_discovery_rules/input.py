"""Define the GetTableDiscoveryRulesUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetTableDiscoveryRulesUseCaseInput:
    """Carry the request to read the discovery rules."""
