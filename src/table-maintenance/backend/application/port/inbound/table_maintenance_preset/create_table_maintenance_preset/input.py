"""Define the CreateTableMaintenancePresetUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CreateTableMaintenancePresetUseCaseInput:
    """Carry the request to create a table maintenance preset."""

    name: str
    settings: dict[str, Any] = field(default_factory=dict)
