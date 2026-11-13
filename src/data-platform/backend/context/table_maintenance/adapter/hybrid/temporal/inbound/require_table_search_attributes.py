"""Define require_table_search_attributes, which checks the namespace before the worker starts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from temporalio.api.enums.v1 import IndexedValueType
from temporalio.api.operatorservice.v1 import ListSearchAttributesRequest

from context.table_maintenance.adapter.hybrid.temporal.inbound.missing_table_search_attributes import (
    MissingTableSearchAttributes,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows import TableSearchAttributeKeys

if TYPE_CHECKING:
    from collections.abc import Sequence

    from temporalio.client import Client
    from temporalio.common import SearchAttributeKey

_TYPE_NAMES = {
    IndexedValueType.INDEXED_VALUE_TYPE_KEYWORD: "Keyword",
    IndexedValueType.INDEXED_VALUE_TYPE_KEYWORD_LIST: "KeywordList",
    IndexedValueType.INDEXED_VALUE_TYPE_TEXT: "Text",
    IndexedValueType.INDEXED_VALUE_TYPE_INT: "Int",
    IndexedValueType.INDEXED_VALUE_TYPE_DOUBLE: "Double",
    IndexedValueType.INDEXED_VALUE_TYPE_BOOL: "Bool",
    IndexedValueType.INDEXED_VALUE_TYPE_DATETIME: "Datetime",
}


async def require_table_search_attributes(
    client: Client, *, required: Sequence[SearchAttributeKey] | None = None
) -> None:
    """Raise ``MissingTableSearchAttributes`` unless every search attribute the workflows set is registered.

    ``required`` defaults to every table search attribute. Each must exist in
    the client's namespace with its own type; the error names each one that
    does not and says to run ``platform/21-temporal/bootstrap.sh``.
    """
    keys = TableSearchAttributeKeys.all() if required is None else tuple(required)
    response = await client.operator_service.list_search_attributes(
        ListSearchAttributesRequest(namespace=client.namespace)
    )
    registered = dict(response.custom_attributes)
    problems = []
    for key in keys:
        wanted = int(key.indexed_value_type)
        have = registered.get(key.name)
        if have is None:
            problems.append(f"{key.name} ({_type_name(wanted)}, missing)")
        elif int(have) != wanted:
            problems.append(f"{key.name} ({_type_name(wanted)}, registered as {_type_name(int(have))})")
    if problems:
        raise MissingTableSearchAttributes(
            f"Temporal namespace {client.namespace!r} lacks search attributes {', '.join(problems)}; "
            "run platform/21-temporal/bootstrap.sh to register them, then restart the worker"
        )


def _type_name(value: int) -> str:
    return _TYPE_NAMES.get(IndexedValueType.ValueType(value), str(value))
