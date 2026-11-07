"""Define the reject_unit_separator function."""

from __future__ import annotations

_SEPARATOR = "\x1f"


def reject_unit_separator(what: str, *values: str) -> None:
    """Raise ValueError when any of ``values`` holds U+001F, which joins the parts of an id.

    An id joins a catalog, namespace parts and a name with U+001F and splits on it again, so
    a component holding it would read back as a different object. ``what`` names the component.
    """
    if any(_SEPARATOR in value for value in values):
        raise ValueError(f"{what} must not contain the unit separator U+001F")
