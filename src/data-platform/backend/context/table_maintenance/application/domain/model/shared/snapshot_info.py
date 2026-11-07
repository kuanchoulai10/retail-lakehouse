"""Define the SnapshotInfo value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from base import ValueObject

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class SnapshotInfo(ValueObject):
    """Identify one snapshot and when it was committed."""

    snapshot_id: int
    committed_at: datetime
