"""Define the DiscoveryAttribute enumeration."""

from __future__ import annotations

from enum import StrEnum


class DiscoveryAttribute(StrEnum):
    """Enumerate what a discovery condition reads of a table.

    ``namespace`` is the dot-joined namespace; ``table_name`` is the table's own name.
    """

    NAMESPACE = "namespace"
    TABLE_NAME = "table_name"
