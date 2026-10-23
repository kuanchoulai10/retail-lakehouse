"""Define the UpdateManagedTableSettingsUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class UpdateManagedTableSettingsUseCaseInput:
    """Carry the request to replace a managed table's settings."""

    uuid: str
    settings: dict[str, Any]
