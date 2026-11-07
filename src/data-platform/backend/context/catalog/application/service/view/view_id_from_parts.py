"""Define the view_id_from_parts function."""

from __future__ import annotations

from context.catalog.application.exceptions import ValidationError
from context.catalog.application.port.outbound.view import ViewId
from context.catalog.application.service.namespace import namespace_id_from_parts


def view_id_from_parts(catalog: str, namespace: list[str], name: str) -> ViewId:
    """Return the id of the view ``name`` in ``namespace`` of ``catalog``, or raise ValidationError.

    The catalog and namespace follow ``namespace_id_from_parts``; the name is not blank and
    holds no U+001F, which joins the parts in a path. Dots and spaces are ordinary characters.
    """
    namespace_id = namespace_id_from_parts(catalog, namespace)
    if not name.strip():
        raise ValidationError("view name must not be blank")
    try:
        return ViewId.of(namespace_id.catalog, namespace_id.parts, name)
    except ValueError as exc:
        raise ValidationError(str(exc)) from None
