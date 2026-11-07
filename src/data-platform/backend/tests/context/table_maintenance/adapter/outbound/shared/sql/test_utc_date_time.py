"""Test the column type and codec that keep datetimes timezone aware in UTC."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import Column, Engine, MetaData, Table, insert, select

from context.table_maintenance.adapter.outbound.shared.sql import (
    IsoDatetimeCodec,
    UtcDateTime,
)


def _table() -> Table:
    return Table("t", MetaData(), Column("at", UtcDateTime))


def test_roundtrip_returns_aware_utc(engine: Engine):
    """A stored datetime comes back timezone aware in UTC."""
    table = _table()
    table.metadata.create_all(engine)
    tz = timezone(timedelta(hours=8))
    with engine.begin() as conn:
        conn.execute(insert(table).values(at=datetime(2026, 1, 1, 8, tzinfo=tz)))
        value = conn.execute(select(table.c.at)).scalar_one()
    assert value == datetime(2026, 1, 1, 0, tzinfo=UTC)
    assert value.tzinfo is not None
    assert value.utcoffset() == timedelta(0)


def test_naive_datetime_rejected(engine: Engine):
    """A naive datetime is rejected when stored."""
    table = _table()
    table.metadata.create_all(engine)
    with pytest.raises(Exception, match="naive"), engine.begin() as conn:
        conn.execute(insert(table).values(at=datetime(2026, 1, 1)))


def test_iso_codec_roundtrip():
    """The ISO codec round trips a datetime and passes None through."""
    value = datetime(2026, 3, 4, 5, 6, 7, tzinfo=UTC)
    encoded = IsoDatetimeCodec.encode(value)
    assert IsoDatetimeCodec.decode(encoded) == value
    assert IsoDatetimeCodec.decode(None) is None
    assert IsoDatetimeCodec.encode(None) is None
    with pytest.raises(ValueError, match="naive"):
        IsoDatetimeCodec.encode(datetime(2026, 1, 1))
