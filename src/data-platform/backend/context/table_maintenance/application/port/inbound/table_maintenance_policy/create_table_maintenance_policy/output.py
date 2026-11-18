"""Define the CreateTableMaintenancePolicyUseCaseOutput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseOutput


class CreateTableMaintenancePolicyUseCaseOutput(UseCaseOutput):
    """Describe the result."""

    name: str
    content: dict[str, Any]
    version: int
    created_at: datetime
    updated_at: datetime
