"""Define the TableDiscoveryRulesId identifier and the id of the one rule list."""

from __future__ import annotations

from base import EntityId


class TableDiscoveryRulesId(EntityId):
    """Identify the TableDiscoveryRules aggregate; there is one per platform."""


GLOBAL_TABLE_DISCOVERY_RULES_ID = TableDiscoveryRulesId("global")
