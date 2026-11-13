"""Define the plan_table_property_reset domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.domain.model.table import (
    TablePropertyDefaultSource,
    TablePropertyNotResettable,
    TablePropertyReset,
)

if TYPE_CHECKING:
    from context.catalog.application.domain.model.table import TableProperty


def _refusal(row: TableProperty) -> str:
    if row.set_by_catalog:
        return f"{row.key} cannot be reset: it is set by the catalog service"
    if row.default_source is TablePropertyDefaultSource.CATALOG_OVERRIDE:
        return f"{row.key} cannot be reset: the catalog forces its value"
    return f"{row.key} cannot be reset: removing it would change the table unsafely"


def plan_table_property_reset(properties: list[TableProperty], keys: list[str]) -> TablePropertyReset:
    """Return the change that resets ``keys`` of a table whose resolved properties are ``properties``.

    A modified key is removed, or written with its default when a new table would hold it
    explicitly (``reset_value``). A key already at its default, or neither known nor set, needs
    no change. Any key that is not resettable refuses the whole reset with
    TablePropertyNotResettable, so a reset never lands in part.
    """
    by_key = {row.key: row for row in properties}
    wanted = sorted(set(keys))
    refused = [_refusal(by_key[key]) for key in wanted if key in by_key and not by_key[key].resettable]
    if refused:
        raise TablePropertyNotResettable("; ".join(refused))
    updates: dict[str, str] = {}
    removals: list[str] = []
    for key in wanted:
        row = by_key.get(key)
        if row is None or not row.modified:
            continue
        value = row.reset_value()
        if value is None:
            removals.append(key)
        else:
            updates[key] = value
    return TablePropertyReset(updates=updates, removals=tuple(removals))
