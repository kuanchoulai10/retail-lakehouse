"""Define the TableDiscoveryRuleId identifier."""

from __future__ import annotations

from typing import ClassVar

from base import EntityId


class TableDiscoveryRuleId(EntityId):
    """Identify one TableDiscoveryRule across the versions of its discovery policy: a ``dr-`` id the platform issues.

    A table records the id of the rule that decided it, so the id is what links the table to its rule
    across versions and edits.
    """

    PREFIX: ClassVar[str | None] = "dr"
