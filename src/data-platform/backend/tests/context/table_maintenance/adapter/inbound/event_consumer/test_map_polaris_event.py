"""Map real and documented Polaris catalog events to table hints."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from context.table_maintenance.adapter.inbound.event_consumer import map_polaris_event
from context.table_maintenance.application.port.inbound.table import (
    ProcessTableHintUseCaseInput,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> bytes:
    return (FIXTURES / f"{name}.json").read_bytes()


def _raw(**fields: object) -> bytes:
    return json.dumps(fields).encode()


def test_update_table_maps_to_table_hint() -> None:
    """An update table event maps to a hint for that table."""
    hint = map_polaris_event(_fixture("after_update_table"))

    assert hint == ProcessTableHintUseCaseInput(
        catalog="iceberg",
        namespace="evt_test",
        table="t1",
        event_type="AFTER_UPDATE_TABLE",
    )


def test_before_create_without_name_maps_to_namespace_hint() -> None:
    """A before-create event without a table name maps to a namespace hint."""
    hint = map_polaris_event(_fixture("before_create_table"))

    assert hint == ProcessTableHintUseCaseInput(
        catalog="iceberg",
        namespace="evt_test",
        table=None,
        event_type="BEFORE_CREATE_TABLE",
    )


def test_before_create_with_name_is_ignored() -> None:
    """A before-create event that names a table is ignored."""
    raw = _raw(
        event_type="BEFORE_CREATE_TABLE",
        catalog_name="iceberg",
        namespace=["a"],
        table_name="t",
    )

    assert map_polaris_event(raw) is None


def test_drop_table_maps_to_table_hint() -> None:
    """A drop table event maps to a hint with its namespace, table and event type."""
    hint = map_polaris_event(_fixture("after_drop_table"))

    assert hint is not None
    assert (hint.namespace, hint.table, hint.event_type) == (
        "evt_test",
        "t1",
        "AFTER_DROP_TABLE",
    )


def test_register_table_maps_to_table_hint() -> None:
    """A register table event maps to a hint for that table."""
    hint = map_polaris_event(_fixture("after_register_table"))

    assert hint == ProcessTableHintUseCaseInput(
        catalog="iceberg",
        namespace="analytics.web",
        table="events",
        event_type="AFTER_REGISTER_TABLE",
    )


def test_create_table_maps_to_table_hint() -> None:
    """A create table event maps to a hint with its namespace and table."""
    raw = _raw(
        event_type="AFTER_CREATE_TABLE",
        catalog_name="iceberg",
        namespace=["sales"],
        table_name="orders",
    )

    hint = map_polaris_event(raw)

    assert hint is not None
    assert (hint.namespace, hint.table) == ("sales", "orders")


def test_rename_table_hints_the_destination() -> None:
    """A rename table event hints the destination table."""
    hint = map_polaris_event(_fixture("after_rename_table"))

    assert hint == ProcessTableHintUseCaseInput(
        catalog="iceberg",
        namespace="sales",
        table="orders",
        event_type="AFTER_RENAME_TABLE",
    )


def test_rename_destination_with_multi_level_namespace() -> None:
    """A rename destination in a multi-level namespace is joined with dots."""
    raw = _raw(
        event_type="AFTER_RENAME_TABLE",
        catalog_name="iceberg",
        source=["a", "b", "old"],
        destination=["a", "b", "new"],
    )

    hint = map_polaris_event(raw)

    assert hint is not None
    assert (hint.namespace, hint.table) == ("a.b", "new")


def test_rename_without_destination_is_skipped() -> None:
    """A rename event without a destination is skipped."""
    raw = _raw(event_type="AFTER_RENAME_TABLE", catalog_name="iceberg")

    assert map_polaris_event(raw) is None


def test_multi_level_namespace_joined_with_dot() -> None:
    """A multi-level namespace is joined with dots."""
    raw = _raw(
        event_type="AFTER_UPDATE_TABLE",
        catalog_name="iceberg",
        namespace=["a", "b", "c"],
        table_name="t",
    )

    hint = map_polaris_event(raw)

    assert hint is not None
    assert hint.namespace == "a.b.c"


@pytest.mark.parametrize("fixture", ["after_refresh_table"])
def test_read_events_ignored(fixture: str) -> None:
    """Read events produce no hint."""
    assert map_polaris_event(_fixture(fixture)) is None


@pytest.mark.parametrize(
    "event_type",
    [
        "BEFORE_LOAD_TABLE",
        "AFTER_LOAD_TABLE",
        "BEFORE_UPDATE_TABLE",
        "BEFORE_DROP_TABLE",
        "AFTER_CREATE_NAMESPACE",
        "AFTER_LIST_NAMESPACES",
    ],
)
def test_other_event_types_are_ignored(event_type: str) -> None:
    """Event types the service does not care about produce no hint."""
    raw = _raw(
        event_type=event_type,
        catalog_name="iceberg",
        namespace=["a"],
        table_name="t",
    )

    assert map_polaris_event(raw) is None


@pytest.mark.parametrize(
    "raw",
    [
        b"not json",
        b"",
        b"[]",
        b'"text"',
        b"\xff\xfe",
        json.dumps({"event_type": "AFTER_UPDATE_TABLE", "namespace": ["a"], "table_name": "t"}).encode(),
        json.dumps({"event_type": "AFTER_UPDATE_TABLE", "catalog_name": "c", "table_name": "t"}).encode(),
        json.dumps(
            {
                "event_type": "AFTER_UPDATE_TABLE",
                "catalog_name": "c",
                "namespace": "a",
                "table_name": "t",
            }
        ).encode(),
        json.dumps({"catalog_name": "c"}).encode(),
    ],
)
def test_malformed_event_is_skipped(raw: bytes) -> None:
    """A malformed event produces no hint."""
    assert map_polaris_event(raw) is None
