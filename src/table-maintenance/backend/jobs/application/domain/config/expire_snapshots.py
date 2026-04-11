from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class ExpireSnapshotsConfig:
    table: str | None = None
    older_than: datetime | None = None
    retain_last: int = 1
    max_concurrent_deletes: int | None = None
    stream_results: bool = False
