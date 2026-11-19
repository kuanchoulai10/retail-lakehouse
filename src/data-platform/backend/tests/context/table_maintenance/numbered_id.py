"""Define the numbered_id test helper."""

from __future__ import annotations


def numbered_id(prefix: str, number: int) -> str:
    """Return a valid ``<prefix>-`` id (docs/adr/0011) whose suffix is ``number`` zero-padded to 26 digits.

    Equal numbers give equal ids and larger numbers sort later, so tests can name ids by number.
    """
    return f"{prefix}-{number:026d}"
