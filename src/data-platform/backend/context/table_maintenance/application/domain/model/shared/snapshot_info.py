"""Define the SnapshotInfo value object."""

from __future__ import annotations

from datetime import datetime

from base import ValueObject


class SnapshotInfo(ValueObject):
    """Identify one snapshot and when it was committed."""

    snapshot_id: int
    committed_at: datetime
