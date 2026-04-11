from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class RemoveOrphanFilesConfig:
    table: str | None = None
    older_than: datetime | None = None
    location: str | None = None
    dry_run: bool = False
    max_concurrent_deletes: int | None = None
