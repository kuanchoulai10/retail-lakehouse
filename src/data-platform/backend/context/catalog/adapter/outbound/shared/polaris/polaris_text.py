"""Define the polaris_text function."""

from __future__ import annotations


def polaris_text(value: object, what: str) -> str:
    """Return ``value`` when it is a JSON string; TypeError naming ``what`` otherwise.

    Nothing is turned into text: a number or a null is refused rather than read as ``"3"`` or ``"None"``.
    """
    if not isinstance(value, str):
        raise TypeError(f"{what} must be text, not {value!r}")
    return value
