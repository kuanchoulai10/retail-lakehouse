"""Define the WholeSeconds duration type."""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from pydantic import PlainSerializer, PlainValidator


def _to_timedelta(value: object) -> timedelta:
    if isinstance(value, timedelta):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return timedelta(seconds=value)
    raise ValueError("must be a timedelta or a whole number of seconds")


def _to_seconds(value: timedelta) -> int:
    seconds = value.total_seconds()
    if not seconds.is_integer():
        raise ValueError(f"duration {value} is not a whole number of seconds")
    return int(seconds)


WholeSeconds = Annotated[
    timedelta,
    PlainValidator(_to_timedelta, json_schema_input_type=int),
    PlainSerializer(_to_seconds, return_type=int, when_used="json"),
]
"""A ``timedelta`` in the domain, integer seconds on the wire.

Validation takes a ``timedelta`` or an ``int`` of seconds (never a
``bool`` or a ``float``). JSON-mode serialization writes an ``int`` and
raises ``ValueError`` for a duration that is not whole seconds.
"""
