"""Define the sort_order_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.application.port.outbound.table import NullOrder, SortDirection, SortField, SortOrder

if TYPE_CHECKING:
    from collections.abc import Mapping


def sort_order_from_polaris(metadata: Mapping[str, Any]) -> SortOrder:
    """Map the default sort order of Iceberg table metadata: ``sort-orders`` at ``default-sort-order-id``."""
    default_id = metadata.get("default-sort-order-id", 0)
    order = next((o for o in metadata.get("sort-orders") or [] if o.get("order-id") == default_id), None)
    if order is None:
        return SortOrder.unsorted()
    return SortOrder(
        order_id=int(order["order-id"]),
        fields=tuple(
            SortField(
                source_id=int(field["source-id"]),
                transform=str(field["transform"]),
                direction=SortDirection(field["direction"]),
                null_order=NullOrder(field["null-order"]),
            )
            for field in order.get("fields", [])
        ),
    )
