"""Test the conversion of partition values to primitives."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from context.table_maintenance.adapter.outbound.table.pyiceberg import (
    partition_value_to_primitive,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (7, 7),
        ("eu", "eu"),
        (date(1970, 1, 11), 10),
        (datetime(1970, 1, 1, 0, 0, 1, 5, tzinfo=UTC), 1_000_005),
        (datetime(1970, 1, 1, 0, 0, 1), 1_000_000),
        (Decimal("1E+2"), "100"),
        (Decimal("-1.50"), "-1.50"),
        (UUID(int=1), "00000000-0000-0000-0000-000000000001"),
        (b"\x01\xff", "01ff"),
    ],
)
def test_converts_to_internal_primitive(value: object, expected: object) -> None:
    """Each supported partition value type converts to its primitive form."""
    assert partition_value_to_primitive(value) == expected


def test_rejects_unknown_types() -> None:
    """A partition value of an unsupported type raises a ValueError."""
    with pytest.raises(ValueError):
        partition_value_to_primitive(object())
