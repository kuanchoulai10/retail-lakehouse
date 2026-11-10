"""Define the polaris_text_map function."""

from __future__ import annotations

from typing import Any


def polaris_text_map(value: Any, what: str) -> dict[str, str]:  # noqa: ANN401
    """Return a copy of ``value``, a JSON object of text values; an absent (None) one is empty.

    Anything else raises TypeError naming ``what``: an empty list or empty text is not read as
    no entries, and a value that is not text is refused rather than turned into text.
    """
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError(f"{what} must be an object, not {value!r}")
    for key, entry in value.items():
        if not isinstance(entry, str):
            raise TypeError(f"{what} value of {key!r} must be text, not {entry!r}")
    return dict(value)
