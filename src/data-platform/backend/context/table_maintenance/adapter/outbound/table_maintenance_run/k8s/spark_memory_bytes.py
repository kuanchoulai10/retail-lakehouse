"""Provide the spark_memory_bytes function."""

from __future__ import annotations

import re

_MEMORY = re.compile(r"^(\d+)([a-z]*)$")
_KIB = 1024
_UNIT_BYTES = {
    "b": 1,
    "k": _KIB,
    "kb": _KIB,
    "m": _KIB**2,
    "mb": _KIB**2,
    "": _KIB**2,
    "g": _KIB**3,
    "gb": _KIB**3,
    "t": _KIB**4,
    "tb": _KIB**4,
}


def spark_memory_bytes(setting: str) -> int:
    """Return a Spark memory setting (``768m``, ``2g``) as bytes; a bare number is MiB, as Spark reads it."""
    match = _MEMORY.match(setting.strip().lower())
    unit = match.group(2) if match else None
    if match is None or unit not in _UNIT_BYTES or int(match.group(1)) <= 0:
        msg = f"cannot read Spark memory setting {setting!r}"
        raise ValueError(msg)
    return int(match.group(1)) * _UNIT_BYTES[unit]
