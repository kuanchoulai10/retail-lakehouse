"""Define the generic_table_id_from_parts function."""

from __future__ import annotations

from context.catalog.application.exceptions import ValidationError
from context.catalog.application.port.outbound.generic_table import GenericTableId
from context.catalog.application.service.namespace import namespace_id_from_parts


def generic_table_id_from_parts(catalog: str, namespace: list[str], name: str) -> GenericTableId:
    """Return the id of the generic table ``name`` in ``namespace`` of ``catalog``, or raise ValidationError.

    The catalog and namespace follow ``namespace_id_from_parts``; the name is not blank and
    holds no U+001F, which joins the parts in a path. Dots and spaces are ordinary characters.
    """
    namespace_id = namespace_id_from_parts(catalog, namespace)
    if not name.strip():
        raise ValidationError("generic table name must not be blank")
    try:
        return GenericTableId.of(namespace_id.catalog, namespace_id.parts, name)
    except ValueError as exc:
        raise ValidationError(str(exc)) from None
