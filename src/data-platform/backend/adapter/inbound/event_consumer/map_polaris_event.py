"""Map a raw Polaris event to a table hint."""

from __future__ import annotations

import logging

from adapter.inbound.event_consumer.parse_polaris_event import parse_polaris_event
from adapter.inbound.event_consumer.polaris_event import PolarisEvent
from application.port.inbound.table import ProcessTableHintUseCaseInput

logger = logging.getLogger(__name__)

_TABLE_EVENTS = frozenset(
    {
        "AFTER_UPDATE_TABLE",
        "AFTER_CREATE_TABLE",
        "AFTER_DROP_TABLE",
        "AFTER_REGISTER_TABLE",
    }
)
_RENAME_EVENT = "AFTER_RENAME_TABLE"
_NAMESPACE_HINT_EVENT = "BEFORE_CREATE_TABLE"


def _hint(
    event: PolarisEvent, namespace: list[str], table: str | None
) -> ProcessTableHintUseCaseInput | None:
    if not namespace:
        raise ValueError("namespace is missing")
    return ProcessTableHintUseCaseInput(
        catalog=event.catalog_name,
        namespace=".".join(namespace),
        table=table,
        event_type=event.event_type,
    )


def _to_hint(event: PolarisEvent) -> ProcessTableHintUseCaseInput | None:
    if event.event_type in _TABLE_EVENTS:
        if not event.table_name:
            raise ValueError("table_name is missing")
        return _hint(event, event.namespace, event.table_name)
    if event.event_type == _RENAME_EVENT:
        if not event.destination or len(event.destination) < 2:
            raise ValueError("destination is missing")
        return _hint(event, event.destination[:-1], event.destination[-1])
    if event.event_type == _NAMESPACE_HINT_EVENT and event.table_name is None:
        return _hint(event, event.namespace, None)
    return None


def map_polaris_event(raw: bytes) -> ProcessTableHintUseCaseInput | None:
    """Return the hint for a table-changing event, or None to skip the record.

    Malformed records are logged at warning level, uninteresting types at debug level.
    """
    try:
        event = parse_polaris_event(raw)
        hint = _to_hint(event)
    except ValueError as exc:
        logger.warning("Skipping malformed Polaris event: %s", exc)
        return None
    if hint is None:
        logger.debug("Ignoring Polaris event type %s", event.event_type)
    return hint
