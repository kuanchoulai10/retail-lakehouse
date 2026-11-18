"""Define the activity_payload helper."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from base import UseCaseOutput


def activity_payload(output: Any) -> dict[str, Any]:  # noqa: ANN401
    """Turn a use-case output into a primitive dict with ISO datetimes.

    A ``UseCaseOutput`` is dumped with ``model_dump()``; a dataclass output (until every port is migrated)
    with ``asdict``. Both then go through the same pass, so a datetime is always ``datetime.isoformat()``
    and the Temporal payload does not change with the migration.
    """
    fields = output.model_dump() if isinstance(output, UseCaseOutput) else asdict(output)
    return _primitive(fields)


def _primitive(value: Any) -> Any:  # noqa: ANN401
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _primitive(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_primitive(item) for item in value]
    return value
