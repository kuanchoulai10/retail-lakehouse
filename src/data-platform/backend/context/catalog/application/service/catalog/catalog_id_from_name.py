"""Define the catalog_id_from_name function."""

from __future__ import annotations

from base.model import validation_message
from context.catalog.application.domain.model.catalog import CatalogId
from context.catalog.application.exceptions import ValidationError


def catalog_id_from_name(name: str) -> CatalogId:
    """Return the id of the catalog called ``name``, or raise ValidationError.

    The name is not blank and holds no U+001F, which joins a catalog to its namespace parts
    in a child's id; such a name would reroute child operations to another catalog.
    """
    if not name.strip():
        raise ValidationError("catalog name must not be blank")
    try:
        return CatalogId.of(name)
    except ValueError as exc:
        raise ValidationError(validation_message(exc)) from None
