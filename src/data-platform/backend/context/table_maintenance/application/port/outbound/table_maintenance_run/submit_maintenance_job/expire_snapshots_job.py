"""Define the ExpireSnapshotsJob."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class ExpireSnapshotsJob:
    """Describe a snapshot expiry: snapshots before ``older_than`` go, except the newest ``retain_last``.

    ``older_than`` is timezone-aware. An option left ``None`` is the procedure's default.
    """

    older_than: datetime
    retain_last: int
    max_concurrent_deletes: int | None = None
    stream_results: bool | None = None
