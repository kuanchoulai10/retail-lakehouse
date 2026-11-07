"""Define the namespace_id_from_parts function."""

from __future__ import annotations

from context.catalog.application.exceptions import ValidationError
from context.catalog.application.port.outbound.namespace import NamespaceId


def namespace_id_from_parts(catalog: str, parts: list[str]) -> NamespaceId:
    """Return the id of the namespace ``parts`` in ``catalog``, or raise ValidationError.

    A namespace has at least one part, no part is blank, and neither the catalog nor a part
    holds U+001F, which joins them in an id. Dots and spaces are ordinary characters of a part.
    """
    if not catalog.strip():
        raise ValidationError("catalog name must not be blank")
    if not parts:
        raise ValidationError("namespace must have at least one part")
    if any(not part.strip() for part in parts):
        raise ValidationError("namespace parts must not be blank")
    try:
        return NamespaceId.of(catalog, tuple(parts))
    except ValueError as exc:
        raise ValidationError(str(exc)) from None
