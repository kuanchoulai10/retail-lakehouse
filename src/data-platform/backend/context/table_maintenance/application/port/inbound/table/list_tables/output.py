"""Define the ListTablesUseCaseOutput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseOutput


class ListTablesUseCaseOutput(UseCaseOutput):
    """Carry the listing."""

    class Table(UseCaseOutput):
        """One entry of the listing."""

        uuid: str
        catalog: str
        namespace: str
        table: str
        status: str
        matched_rule_id: str | None
        operation_states: dict[str, dict[str, Any]]
        registered_at: datetime
        updated_at: datetime
        last_committed_at: datetime | None
        last_discovered_at: datetime | None

    items: tuple[Table, ...]
