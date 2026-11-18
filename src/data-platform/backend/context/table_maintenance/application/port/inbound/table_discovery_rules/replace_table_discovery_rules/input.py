"""Define the ReplaceTableDiscoveryRulesUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class ReplaceTableDiscoveryRulesUseCaseInput(UseCaseInput):
    """Carry the whole new rule list and the version it was edited from."""

    class TableDiscoveryRule(UseCaseInput):
        """One rule of the new list; a rule without an id is new and gets one."""

        id: str | None
        priority: int
        action: str
        enabled: bool
        catalogs: tuple[str, ...]
        namespaces: tuple[str, ...]
        tables: tuple[str, ...]

    version: int
    rules: tuple[TableDiscoveryRule, ...]
