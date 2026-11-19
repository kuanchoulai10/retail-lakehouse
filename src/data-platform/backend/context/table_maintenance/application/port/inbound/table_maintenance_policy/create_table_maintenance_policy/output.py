"""Define the CreateTableMaintenancePolicyUseCaseOutput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseOutput


class CreateTableMaintenancePolicyUseCaseOutput(UseCaseOutput):
    """Describe the result: the new policy's ``mp-`` id, its name and its first version."""

    id: str
    name: str
    is_default: bool
    content: dict[str, Any]
    version: int
    created_at: datetime
    updated_at: datetime
