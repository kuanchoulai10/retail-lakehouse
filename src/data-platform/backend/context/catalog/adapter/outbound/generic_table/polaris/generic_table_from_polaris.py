"""Define the generic_table_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.shared.polaris import read_polaris_reply
from context.catalog.application.port.outbound.generic_table import GenericTable

if TYPE_CHECKING:
    from collections.abc import Mapping

    import httpx

    from context.catalog.application.port.outbound.generic_table import GenericTableId


def _optional_text(table: Mapping[str, Any], key: str) -> str | None:
    value = table.get(key)
    if value is not None and not isinstance(value, str):
        raise TypeError(f"{key} must be text, not {value!r}")
    return value


def _properties(table: Mapping[str, Any]) -> dict[str, str]:
    properties = table.get("properties") or {}
    if not isinstance(properties, dict):
        raise TypeError(f"properties must be an object, not {properties!r}")
    return {str(key): str(value) for key, value in properties.items()}


def _generic_table(table_id: GenericTableId, table: Mapping[str, Any]) -> GenericTable:
    format_ = table["format"]
    if not isinstance(format_, str):
        raise TypeError(f"format must be text, not {format_!r}")
    return GenericTable(
        id=table_id,
        format=format_,
        base_location=_optional_text(table, "base-location"),
        doc=_optional_text(table, "doc"),
        properties=_properties(table),
    )


def _table_object(body: dict[str, Any]) -> dict[str, Any]:
    table = body["table"]
    if not isinstance(table, dict):
        raise TypeError(f"table must be an object, not {table!r}")
    return table


def generic_table_from_polaris(table_id: GenericTableId, response: httpx.Response) -> GenericTable:
    """Map the ``table`` of a LoadGenericTableResponse reply to a GenericTable.

    A reply that is not JSON, has no ``table``, or holds a table this backend cannot read
    raises CatalogUnavailableError naming the table, so the API answers 502 rather than 500.
    """
    return read_polaris_reply(
        response, f"generic table {table_id.name}", lambda body: _generic_table(table_id, _table_object(body))
    )
