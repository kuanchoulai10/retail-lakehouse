"""Define the UpdateTableMaintenancePolicyUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class UpdateTableMaintenancePolicyUseCaseInput:
    """Carry the request to replace a table maintenance policy's content as a new version."""

    name: str
    content: dict[str, Any]
    version: int
