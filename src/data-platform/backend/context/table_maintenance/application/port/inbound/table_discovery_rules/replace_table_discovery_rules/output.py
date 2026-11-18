"""Define the ReplaceTableDiscoveryRulesUseCaseOutput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseOutput


class ReplaceTableDiscoveryRulesUseCaseOutput(UseCaseOutput):
    """Carry the discovery rules in priority order and the list's version."""

    class TableDiscoveryRule(UseCaseOutput):
        """One discovery rule."""

        id: str
        priority: int
        action: str
        enabled: bool
        catalogs: tuple[str, ...]
        namespaces: tuple[str, ...]
        tables: tuple[str, ...]
        created_at: datetime
        updated_at: datetime

    version: int
    rules: tuple[TableDiscoveryRule, ...]
