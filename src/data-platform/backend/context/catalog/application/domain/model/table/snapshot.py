"""Define the Snapshot value object."""

from __future__ import annotations

from base import ValueObject


class Snapshot(ValueObject):
    """One snapshot of a table: its id, its parent, when it was made, by which operation, and its summary.

    ``schema_id`` is the id of the schema the snapshot was written with; format v1 does not record it.
    ``summary`` holds the snapshot summary's other keys (``added-records``, ``total-records``
    and so on) as the catalog reports them, as text.
    """

    snapshot_id: int
    parent_id: int | None
    timestamp_ms: int
    schema_id: int | None = None
    operation: str | None
    summary: dict[str, str]
