"""Define the activity_payload helper."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any


def activity_payload(output: Any) -> dict[str, Any]:  # noqa: ANN401
    """Turn a use-case output dataclass into a primitive dict with ISO datetimes."""
    return _primitive(asdict(output))


def _primitive(value: Any) -> Any:  # noqa: ANN401
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _primitive(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_primitive(item) for item in value]
    return value
