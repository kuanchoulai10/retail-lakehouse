"""Define the TableDiscoveryRuleId identifier."""

from __future__ import annotations

from typing import ClassVar

from base import EntityId


class TableDiscoveryRuleId(EntityId):
    """Identify one TableDiscoveryRule within the discovery rules; the platform mints it as a ``dr-`` id."""

    PREFIX: ClassVar[str | None] = "dr"
