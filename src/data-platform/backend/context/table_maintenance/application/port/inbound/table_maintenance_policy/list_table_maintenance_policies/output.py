"""Define the ListTableMaintenancePoliciesUseCaseOutput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseOutput


class ListTableMaintenancePoliciesUseCaseOutput(UseCaseOutput):
    """Carry the listing."""

    class TableMaintenancePolicy(UseCaseOutput):
        """One entry of the listing."""

        name: str
        content: dict[str, Any]
        version: int
        created_at: datetime
        updated_at: datetime
        attachment_count: int

    items: tuple[TableMaintenancePolicy, ...]
