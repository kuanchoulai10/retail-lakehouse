"""Define the resolve_table_properties domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.domain.model.table import (
    TableProperty,
    TablePropertyDefaultSource,
)

if TYPE_CHECKING:
    from context.catalog.application.domain.model.catalog import Catalog
    from context.catalog.application.domain.model.table import (
        Table,
        TablePropertyCatalogue,
        TablePropertyDefinition,
    )

_FORMAT_VERSION = "format-version"


def _current_values(table: Table) -> dict[str, str]:
    """Return the properties the table sets, plus its format version, which Iceberg keeps out of them."""
    current = dict(table.properties)
    if table.format_version is not None:
        current[_FORMAT_VERSION] = str(table.format_version)
    return current


def _default_of(
    key: str, catalog: Catalog, definition: TablePropertyDefinition | None
) -> tuple[str | None, TablePropertyDefaultSource | None]:
    """Return the default of ``key`` and where it comes from: catalog override, catalog default, then Iceberg.

    A key the catalog service sets itself has neither.
    """
    if definition is not None and definition.set_by_catalog:
        return None, None
    overrides = catalog.table_property_overrides
    if key in overrides:
        return overrides[key], TablePropertyDefaultSource.CATALOG_OVERRIDE
    defaults = catalog.table_property_defaults
    if key in defaults:
        return defaults[key], TablePropertyDefaultSource.CATALOG
    if definition is not None:
        return definition.iceberg_default, TablePropertyDefaultSource.ICEBERG
    return None, None


def _resolve(
    key: str, current: str | None, catalog: Catalog, definition: TablePropertyDefinition | None
) -> TableProperty:
    default, source = _default_of(key, catalog, definition)
    forced = source is TablePropertyDefaultSource.CATALOG_OVERRIDE
    safe_to_reset = definition is None or definition.resettable
    written_on_create = definition is not None and definition.written_on_create
    new_table_holds_it = source is TablePropertyDefaultSource.CATALOG or (
        source is TablePropertyDefaultSource.ICEBERG and written_on_create
    )
    return TableProperty(
        key=key,
        current_value=current,
        default_value=default,
        default_source=source,
        description=None if definition is None else definition.description,
        custom=definition is None,
        resettable=safe_to_reset and not forced,
        reset_writes_default=new_table_holds_it,
        set_by_catalog=definition is not None and definition.set_by_catalog,
    )


def resolve_table_properties(table: Table, catalog: Catalog, catalogue: TablePropertyCatalogue) -> list[TableProperty]:
    """Return every property of ``table`` next to its default, ordered by key.

    The rows are every key the catalogue knows, every key the table sets and every key the
    catalog defaults or forces. A key's default is the catalog's ``table-override.<key>``
    (forced, so never resettable), else its ``table-default.<key>``, else Iceberg's default.
    Both catalog properties apply only when a table is created, so a reset writes a catalog
    default back instead of removing the key, which would fall back to Iceberg's.
    """
    current = _current_values(table)
    keys = (
        {definition.key for definition in catalogue.definitions}
        | set(current)
        | set(catalog.table_property_defaults)
        | set(catalog.table_property_overrides)
    )
    return [_resolve(key, current.get(key), catalog, catalogue.definition_of(key)) for key in sorted(keys)]
