"""Define the memory_bytes function."""

from __future__ import annotations

import re

_UNITS = {"b": 1, "k": 1024, "m": 1024**2, "g": 1024**3, "t": 1024**4}
_SIZE = re.compile(r"(\d+)([bkmgt]?)")


def memory_bytes(value: str) -> int:
    """Return the bytes of a Spark memory size such as ``768m`` or ``1g``; no suffix means MiB."""
    match = _SIZE.fullmatch(value.strip().lower())
    if match is None:
        msg = f"not a Spark memory size: {value!r}"
        raise ValueError(msg)
    number, unit = match.groups()
    return int(number) * _UNITS[unit or "m"]
