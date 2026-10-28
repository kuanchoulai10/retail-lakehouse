"""Define the UpdateDiscoveryRuleUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateDiscoveryRuleUseCaseInput:
    """Carry the request to replace a discovery rule's definition."""

    id: str
    priority: int
    effect: str
    catalog_pattern: str = "*"
    namespace_pattern: str = "*"
    table_pattern: str = "*"
    preset_id: str | None = None
    enabled: bool = True
