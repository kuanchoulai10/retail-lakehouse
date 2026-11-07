"""Define the namespace_parts_from_polaris function."""

from __future__ import annotations

from typing import Any


def namespace_parts_from_polaris(value: Any) -> tuple[str, ...]:  # noqa: ANN401
    """Return the parts of an Iceberg REST namespace, a JSON list of strings; TypeError otherwise.

    A string is refused rather than split into characters, and a non-string part is refused
    rather than turned into text, so a reply of the wrong shape never names another namespace.
    """
    if not isinstance(value, list) or not all(isinstance(part, str) for part in value):
        raise TypeError(f"namespace must be a list of strings, not {value!r}")
    return tuple(value)
