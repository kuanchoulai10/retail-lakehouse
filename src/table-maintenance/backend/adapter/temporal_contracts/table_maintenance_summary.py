"""Define the table_maintenance_summary helper."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


def table_maintenance_summary(table_name: str, operations: Iterable[str]) -> str:
    """Return the static summary of a maintenance run: its table and operations."""
    return f"{table_name} · {', '.join(operations)}"
