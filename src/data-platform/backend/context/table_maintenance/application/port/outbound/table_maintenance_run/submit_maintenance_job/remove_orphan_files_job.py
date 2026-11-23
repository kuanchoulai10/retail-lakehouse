"""Define the RemoveOrphanFilesJob."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class RemoveOrphanFilesJob:
    """Describe an orphan file removal: files no snapshot holds, written before ``older_than``.

    ``older_than`` is timezone-aware. An option left ``None`` is the procedure's default.
    """

    older_than: datetime
    max_concurrent_deletes: int | None = None
    prefix_mismatch_mode: str | None = None
