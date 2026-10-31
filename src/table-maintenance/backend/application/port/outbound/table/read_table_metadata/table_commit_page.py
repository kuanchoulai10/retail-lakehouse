"""Define the TableCommitPage."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TableCommitPage:
    """A page of a table's commits, newest first.

    ``commits`` items are ``{"snapshot_id", "parent_id", "committed_at",
    "operation", "summary", "writer"}``. ``truncated`` is true when more commits
    exist than the page holds. ``table_uuid`` is the catalog's uuid of the
    table the page was read from.
    """

    table_uuid: str
    commits: list[dict[str, Any]] = field(default_factory=list)
    truncated: bool = False
