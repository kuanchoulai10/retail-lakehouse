"""Define the PreviewTableDiscoveryRulesUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PreviewTableDiscoveryRulesUseCaseOutputItem:
    """One table and how the candidate rules decide it.

    ``rule_id`` names the deciding rule, as ``#<index>`` in the candidate list
    for a rule without an id, or is None when no rule matches.
    """

    catalog: str
    namespace: str
    table: str
    rule_id: str | None
    managed: bool


@dataclass(frozen=True)
class PreviewTableDiscoveryRulesUseCaseOutput:
    """Carry every table of the covered catalogs with its decision, and the counts."""

    tables: list[PreviewTableDiscoveryRulesUseCaseOutputItem]
    managed: int
    unmanaged: int
