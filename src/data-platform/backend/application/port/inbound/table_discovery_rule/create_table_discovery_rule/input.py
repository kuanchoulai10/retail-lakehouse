"""Define the CreateTableDiscoveryRuleUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CreateTableDiscoveryRuleUseCaseInput:
    """Carry the request to create a discovery rule."""

    priority: int
    effect: str
    catalog_pattern: str = "*"
    namespace_pattern: str = "*"
    table_pattern: str = "*"
    preset_id: str | None = None
    enabled: bool = True
