"""Define the TableDiscoveryRulesRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod

from base import Repository
from context.table_maintenance.application.domain.model.table_discovery_rules import (
    TableDiscoveryRules,
)


class TableDiscoveryRulesRepo(Repository[TableDiscoveryRules]):
    """Persist the platform's one TableDiscoveryRules aggregate."""

    @abstractmethod
    def get_rules(self) -> TableDiscoveryRules:
        """Return the discovery rules; empty at version 0 when none were ever saved."""

    @abstractmethod
    def save(self, rules: TableDiscoveryRules) -> TableDiscoveryRules:
        """Store the replaced list atomically and return it.

        Raise ``StaleDiscoveryRulesVersion`` when the stored version is not the
        one the list was replaced from (``rules.version - 1``).
        """
