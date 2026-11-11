"""Define the GetTableDiscoveryRulesUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class GetTableDiscoveryRulesUseCaseOutputItem:
    """One discovery rule."""

    id: str
    priority: int
    action: str
    enabled: bool
    catalogs: list[str]
    namespaces: list[str]
    tables: list[str]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class GetTableDiscoveryRulesUseCaseOutput:
    """Carry the discovery rules in priority order and the list's version."""

    version: int
    rules: list[GetTableDiscoveryRulesUseCaseOutputItem]
