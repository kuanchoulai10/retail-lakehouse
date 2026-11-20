"""Define the typed keys of the table search attributes."""

from __future__ import annotations

from typing import ClassVar

from temporalio.common import SearchAttributeKey

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TableSearchAttribute,
)


class TableSearchAttributeKeys:
    """Hold the typed key of each table search attribute: keywords, and a keyword list of operations."""

    TABLE_UUID: ClassVar[SearchAttributeKey[str]] = SearchAttributeKey.for_keyword(TableSearchAttribute.TABLE_UUID)
    TABLE_NAME: ClassVar[SearchAttributeKey[str]] = SearchAttributeKey.for_keyword(TableSearchAttribute.TABLE_NAME)
    MAINTENANCE_OPERATIONS: ClassVar[SearchAttributeKey] = SearchAttributeKey.for_keyword_list(
        TableSearchAttribute.MAINTENANCE_OPERATIONS
    )
    MAINTENANCE_TRIGGER: ClassVar[SearchAttributeKey[str]] = SearchAttributeKey.for_keyword(
        TableSearchAttribute.MAINTENANCE_TRIGGER
    )

    @classmethod
    def all(cls) -> tuple[SearchAttributeKey, ...]:
        """Return every key, in the order the Temporal wave registers them."""
        return (
            cls.TABLE_UUID,
            cls.TABLE_NAME,
            cls.MAINTENANCE_OPERATIONS,
            cls.MAINTENANCE_TRIGGER,
        )
