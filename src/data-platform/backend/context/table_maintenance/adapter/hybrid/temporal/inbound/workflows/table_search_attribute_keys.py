"""Define the typed keys of the table search attributes."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from temporalio.common import SearchAttributeKey

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TableSearchAttribute,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class TableSearchAttributeKeys:
    """Hold the typed key of each table search attribute: keywords, and keyword lists of operations and tables."""

    TABLE_UUID: ClassVar[SearchAttributeKey[str]] = SearchAttributeKey.for_keyword(TableSearchAttribute.TABLE_UUID)
    TABLE_NAME: ClassVar[SearchAttributeKey[str]] = SearchAttributeKey.for_keyword(TableSearchAttribute.TABLE_NAME)
    MAINTENANCE_OPERATIONS: ClassVar[SearchAttributeKey] = SearchAttributeKey.for_keyword_list(
        TableSearchAttribute.MAINTENANCE_OPERATIONS
    )
    MAINTENANCE_TRIGGER: ClassVar[SearchAttributeKey[str]] = SearchAttributeKey.for_keyword(
        TableSearchAttribute.MAINTENANCE_TRIGGER
    )
    GRANTED_TABLE_UUIDS: ClassVar[SearchAttributeKey[Sequence[str]]] = SearchAttributeKey.for_keyword_list(
        TableSearchAttribute.GRANTED_TABLE_UUIDS
    )

    @classmethod
    def all(cls) -> tuple[SearchAttributeKey, ...]:
        """Return every key, in the order the Temporal wave registers them."""
        return (
            cls.TABLE_UUID,
            cls.TABLE_NAME,
            cls.MAINTENANCE_OPERATIONS,
            cls.MAINTENANCE_TRIGGER,
            cls.GRANTED_TABLE_UUIDS,
        )
