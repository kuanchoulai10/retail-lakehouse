"""Define the helper that registers the table search attributes on a test server."""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio.api.enums.v1 import IndexedValueType
from temporalio.api.operatorservice.v1 import AddSearchAttributesRequest

from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows import (
    TableSearchAttributeKeys,
)

if TYPE_CHECKING:
    from temporalio.client import Client


async def register_table_search_attributes(client: Client, namespace: str = "default") -> None:
    """Register every table search attribute, as the Temporal wave does on the cluster."""
    await client.operator_service.add_search_attributes(
        AddSearchAttributesRequest(
            namespace=namespace,
            search_attributes={
                key.name: IndexedValueType.ValueType(int(key.indexed_value_type))
                for key in TableSearchAttributeKeys.all()
            },
        )
    )
