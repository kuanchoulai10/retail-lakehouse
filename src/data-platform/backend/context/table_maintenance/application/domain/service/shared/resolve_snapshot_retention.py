"""Define the resolve_snapshot_retention domain service."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import (
    MAX_AGE,
    MAX_SNAPSHOTS_TO_KEEP,
    SnapshotRetention,
)
from context.table_maintenance.application.domain.service.shared.positive_int_property import (
    positive_int_property,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from context.table_maintenance.application.domain.model.table_maintenance_policy import (
        ExpireSnapshotsTarget,
    )

MIN_SNAPSHOTS_TO_KEEP_PROPERTY = "history.expire.min-snapshots-to-keep"
MAX_SNAPSHOT_AGE_MS_PROPERTY = "history.expire.max-snapshot-age-ms"
DEFAULT_MIN_SNAPSHOTS_TO_KEEP = 1
DEFAULT_MAX_SNAPSHOT_AGE = timedelta(days=5)


def resolve_snapshot_retention(
    target: ExpireSnapshotsTarget | None, properties: Mapping[str, str]
) -> SnapshotRetention:
    """Return the retention of a table: each value the target's, else the table property's, else Iceberg's default.

    The age property is in milliseconds; it is floored to whole seconds, and an age under one second
    is ignored like a malformed one. A property over what Iceberg and a date can hold is clamped, not
    ignored: an age over 100 years (Iceberg's ``Long.MAX`` "never by age") to 100 years, a count over
    a Java ``int`` to the largest one.
    """
    minimum = None if target is None else target.min_snapshots_to_keep
    if minimum is None:
        minimum = _property_count(properties) or DEFAULT_MIN_SNAPSHOTS_TO_KEEP
    age = None if target is None else target.max_snapshot_age
    if age is None:
        age = _property_age(properties) or DEFAULT_MAX_SNAPSHOT_AGE
    return SnapshotRetention(min_snapshots_to_keep=minimum, max_snapshot_age=age)


def _property_age(properties: Mapping[str, str]) -> timedelta | None:
    millis = positive_int_property(properties, MAX_SNAPSHOT_AGE_MS_PROPERTY)
    if millis is None or millis < 1000:
        return None
    return timedelta(seconds=min(millis // 1000, MAX_AGE // timedelta(seconds=1)))


def _property_count(properties: Mapping[str, str]) -> int | None:
    count = positive_int_property(properties, MIN_SNAPSHOTS_TO_KEEP_PROPERTY)
    return None if count is None else min(count, MAX_SNAPSHOTS_TO_KEEP)
