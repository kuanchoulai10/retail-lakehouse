"""Define the GetTableUseCaseOutput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseOutput


class GetTableUseCaseOutput(UseCaseOutput):
    """Describe the table after the operation."""

    uuid: str
    catalog: str
    namespace: str
    table: str
    status: str
    priority: str
    decided_by: dict[str, Any] | None
    operation_states: dict[str, dict[str, Any]]
    registered_at: datetime
    updated_at: datetime
    last_committed_at: datetime | None
    last_discovered_at: datetime | None
