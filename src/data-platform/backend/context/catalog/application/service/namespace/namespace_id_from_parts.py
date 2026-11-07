"""Define the namespace_id_from_parts function."""

from __future__ import annotations

from context.catalog.application.exceptions import ValidationError
from context.catalog.application.port.outbound.namespace import NamespaceId

_SEPARATOR = "\x1f"


def namespace_id_from_parts(catalog: str, parts: list[str]) -> NamespaceId:
    """Return the id of the namespace ``parts`` in ``catalog``, or raise ValidationError.

    A namespace has at least one part, no part is blank, and no part holds U+001F, which joins
    the parts in a path. Dots and spaces are ordinary characters of a part.
    """
    if not catalog.strip():
        raise ValidationError("catalog name must not be blank")
    if not parts:
        raise ValidationError("namespace must have at least one part")
    for part in parts:
        if not part.strip():
            raise ValidationError("namespace parts must not be blank")
        if _SEPARATOR in part:
            raise ValidationError("namespace parts must not contain the unit separator U+001F")
    return NamespaceId.of(catalog, tuple(parts))
