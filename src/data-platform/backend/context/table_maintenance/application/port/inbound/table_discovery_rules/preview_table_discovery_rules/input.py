"""Define the PreviewTableDiscoveryRulesUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PreviewTableDiscoveryRulesUseCaseInputItem:
    """One rule of the candidate list; a rule without an id is unsaved."""

    id: str | None
    priority: int
    action: str
    enabled: bool
    catalogs: list[str]
    namespaces: list[str]
    tables: list[str]


@dataclass(frozen=True)
class PreviewTableDiscoveryRulesUseCaseInput:
    """Carry the whole candidate rule list, unsaved."""

    rules: list[PreviewTableDiscoveryRulesUseCaseInputItem]
