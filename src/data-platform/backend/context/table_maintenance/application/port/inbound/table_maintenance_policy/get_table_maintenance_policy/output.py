"""Define the GetTableMaintenancePolicyUseCaseOutput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseOutput


class GetTableMaintenancePolicyUseCaseOutput(UseCaseOutput):
    """Describe the result: the policy's ``mp-`` id, its name and its current version."""

    id: str
    name: str
    content: dict[str, Any]
    version: int
    created_at: datetime
    updated_at: datetime
