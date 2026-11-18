"""Define the activity_payload helper."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from base import UseCaseOutput


def activity_payload(output: UseCaseOutput) -> dict[str, Any]:
    """Turn a use-case output into a primitive dict with ISO datetimes.

    The output is dumped with ``model_dump()`` and every datetime is written by ``datetime.isoformat()``, so the
    Temporal payload holds only JSON primitives.
    """
    return _primitive(output.model_dump())


def _primitive(value: Any) -> Any:  # noqa: ANN401
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _primitive(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_primitive(item) for item in value]
    return value
