"""Define the raise_not_in_catalog function."""

from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn

from application.exceptions import NotFoundError

if TYPE_CHECKING:
    from application.domain.model.table import Table


def raise_not_in_catalog(table: Table) -> NoReturn:
    """Raise NotFoundError for a registered table the catalog no longer has."""
    name = table.name
    raise NotFoundError(
        f"table {name.catalog}.{name.namespace}.{name.table} is not in the catalog"
    )
