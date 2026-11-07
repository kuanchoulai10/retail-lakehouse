"""Parse raw Kafka bytes into a PolarisEvent."""

from __future__ import annotations

import json

from context.table_maintenance.adapter.inbound.event_consumer.polaris_event import (
    PolarisEvent,
)


def _string_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list of strings")
    items = [item for item in value if isinstance(item, str)]
    if len(items) != len(value):
        raise ValueError(f"{field} must be a list of strings")
    return items


def parse_polaris_event(raw: bytes) -> PolarisEvent:
    """Decode a Polaris event payload, raising ValueError when it is malformed."""
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"event is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("event must be a JSON object")
    event_type = data.get("event_type")
    catalog_name = data.get("catalog_name")
    if not isinstance(event_type, str) or not event_type:
        raise ValueError("event_type is missing")
    if not isinstance(catalog_name, str) or not catalog_name:
        raise ValueError("catalog_name is missing")
    table_name = data.get("table_name")
    if table_name is not None and not isinstance(table_name, str):
        raise ValueError("table_name must be a string")
    event_id = data.get("event_id")
    destination = data.get("destination")
    return PolarisEvent(
        event_type=event_type,
        catalog_name=catalog_name,
        namespace=_string_list(data.get("namespace", []), "namespace"),
        table_name=table_name,
        event_id=event_id if isinstance(event_id, str) else None,
        destination=(None if destination is None else _string_list(destination, "destination")),
    )
