"""Test which properties a reset to default removes or writes, and which it refuses."""

from __future__ import annotations

import pytest

from context.catalog.application.domain.model.table import (
    TableProperty,
    TablePropertyDefaultSource,
    TablePropertyNotResettable,
    TablePropertyReset,
)
from context.catalog.application.domain.service.table import plan_table_property_reset

ICEBERG = TablePropertyDefaultSource.ICEBERG


def _row(
    key: str,
    current: str | None,
    default: str | None = "d",
    *,
    source: TablePropertyDefaultSource | None = ICEBERG,
    custom: bool = False,
    resettable: bool = True,
    writes_default: bool = False,
) -> TableProperty:
    return TableProperty(
        key=key,
        current_value=current,
        default_value=default,
        default_source=source,
        description=None if custom else "A property.",
        custom=custom,
        resettable=resettable,
        reset_writes_default=writes_default,
    )


ROWS = [
    _row("a", "changed"),
    _row("b", "d"),
    _row("c", None),
    _row("codec", "gzip", "zstd", writes_default=True),
    _row("owner", "x", None, source=None, custom=True),
    _row("format-version", "2", "2", resettable=False),
    _row("forced", "x", "y", source=TablePropertyDefaultSource.CATALOG_OVERRIDE, resettable=False),
]


def test_reset_removes_modified_keys_and_writes_keys_a_new_table_holds():
    """A modified key is removed, or written with its default when a new table would hold it."""
    reset = plan_table_property_reset(ROWS, ["a", "codec", "owner"])

    assert reset == TablePropertyReset(updates={"codec": "zstd"}, removals=("a", "owner"))


def test_reset_skips_keys_already_at_their_default_or_unknown():
    """A key that is not modified, or is neither known nor set, needs no change."""
    reset = plan_table_property_reset(ROWS, ["b", "c", "nowhere"])

    assert reset.is_empty


def test_reset_lists_each_key_once():
    """A key named twice is changed once."""
    assert plan_table_property_reset(ROWS, ["a", "a"]).removals == ("a",)


@pytest.mark.parametrize(
    ("key", "reason"),
    [("format-version", "would change the table unsafely"), ("forced", "the catalog forces its value")],
)
def test_reset_refuses_a_key_that_is_not_resettable(key: str, reason: str):
    """A non-resettable key refuses the whole reset and says why."""
    with pytest.raises(TablePropertyNotResettable, match=reason):
        plan_table_property_reset(ROWS, ["a", key])
