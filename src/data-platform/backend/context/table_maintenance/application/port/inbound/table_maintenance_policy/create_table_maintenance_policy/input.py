"""Define the CreateTableMaintenancePolicyUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CreateTableMaintenancePolicyUseCaseInput:
    """Carry the request to create a table maintenance policy at version 1."""

    name: str
    content: dict[str, Any]
