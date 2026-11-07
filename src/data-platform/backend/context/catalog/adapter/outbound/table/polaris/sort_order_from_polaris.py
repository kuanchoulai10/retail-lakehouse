"""Define the sort_order_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.application.port.outbound.table import NullOrder, SortDirection, SortField, SortOrder

if TYPE_CHECKING:
    from collections.abc import Mapping


def _field(field: Mapping[str, Any]) -> SortField:
    return SortField(
        source_id=int(field["source-id"]),
        transform=str(field["transform"]),
        direction=SortDirection(field["direction"]),
        null_order=NullOrder(field["null-order"]),
    )


def sort_order_from_polaris(metadata: Mapping[str, Any]) -> SortOrder:
    """Map the default sort order of Iceberg table metadata: ``sort-orders`` at ``default-sort-order-id``.

    Without ``default-sort-order-id`` (format v1) the table is unsorted. A default id that
    matches no order, or an unknown direction or null order, raises ValueError.
    """
    if "default-sort-order-id" not in metadata:
        return SortOrder.unsorted()
    default_id = metadata["default-sort-order-id"]
    for order in metadata["sort-orders"]:
        if order["order-id"] == default_id:
            return SortOrder(order_id=int(default_id), fields=tuple(_field(f) for f in order["fields"]))
    raise ValueError(f"default-sort-order-id {default_id} matches no sort order")
