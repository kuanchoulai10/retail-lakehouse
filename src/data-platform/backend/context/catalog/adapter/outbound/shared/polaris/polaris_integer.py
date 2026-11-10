"""Define the polaris_integer function."""

from __future__ import annotations


def polaris_integer(value: object, what: str) -> int:
    """Return ``value`` when it is a JSON integer; TypeError naming ``what`` otherwise.

    Nothing is coerced: a bool, a float such as ``3.0`` and text such as ``"3"`` are refused,
    so a reply of the wrong shape never becomes a different number.
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{what} must be an integer, not {value!r}")
    return value
