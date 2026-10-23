"""Define the UpdateDiscoveryRuleUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class UpdateDiscoveryRuleUseCaseOutput:
    """Describe the discovery rule."""

    id: str
    priority: int
    effect: str
    catalog_pattern: str
    namespace_pattern: str
    table_pattern: str
    template_id: str | None
    enabled: bool
    created_at: datetime
    updated_at: datetime
