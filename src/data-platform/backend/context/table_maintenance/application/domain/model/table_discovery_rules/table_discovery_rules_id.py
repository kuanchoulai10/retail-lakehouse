"""Define the TableDiscoveryRulesId identifier and the id of the one rule list."""

from __future__ import annotations

from typing import ClassVar

from base import EntityId


class TableDiscoveryRulesId(EntityId):
    """Identify the TableDiscoveryRules aggregate; there is one per platform, with a fixed ``dp-`` id."""

    PREFIX: ClassVar[str | None] = "dp"


GLOBAL_TABLE_DISCOVERY_RULES_ID = TableDiscoveryRulesId("dp-00000000000000000000000000")
