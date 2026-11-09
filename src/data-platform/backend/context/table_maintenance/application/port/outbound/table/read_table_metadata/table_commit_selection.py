"""Define the TableCommitSelection."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableCommitSelection:
    """Select which commits of a table to list, newest first.

    ``since`` keeps commits at or after an ISO timestamp, ``before`` keeps commits strictly
    before one, and ``writer`` keeps one writer's commits; the filters apply before ``limit``.
    """

    limit: int
    since: str | None = None
    before: str | None = None
    writer: str | None = None
