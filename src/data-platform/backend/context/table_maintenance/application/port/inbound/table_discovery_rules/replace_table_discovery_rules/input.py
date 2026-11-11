"""Define the ReplaceTableDiscoveryRulesUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReplaceTableDiscoveryRulesUseCaseInputItem:
    """One rule of the new list; a rule without an id is new and gets one."""

    id: str | None
    priority: int
    action: str
    enabled: bool
    catalogs: list[str]
    namespaces: list[str]
    tables: list[str]


@dataclass(frozen=True)
class ReplaceTableDiscoveryRulesUseCaseInput:
    """Carry the whole new rule list and the version it was edited from."""

    version: int
    rules: list[ReplaceTableDiscoveryRulesUseCaseInputItem]
