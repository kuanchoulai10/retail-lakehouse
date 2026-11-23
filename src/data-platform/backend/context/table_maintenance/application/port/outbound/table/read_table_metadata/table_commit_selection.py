"""Define the TableCommitSelection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class TableCommitSelection:
    """Select which commits of a table to list, newest first.

    ``since`` keeps commits at or after a time, ``before`` keeps commits strictly before one
    (a time without a zone is UTC), and ``writer`` keeps one writer's commits; the filters apply before ``limit``.
    """

    limit: int
    since: datetime | None = None
    before: datetime | None = None
    writer: str | None = None
