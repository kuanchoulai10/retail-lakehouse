"""Define the TableMaintenancePolicyName identifier."""

from __future__ import annotations

import re

from pydantic import field_validator

from base import EntityId

_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class TableMaintenancePolicyName(EntityId):
    """Identify a TableMaintenancePolicy by its name: 1 to 64 letters, digits, ``_`` or ``-``."""

    @field_validator("root")
    @classmethod
    def _matches_pattern(cls, value: str) -> str:
        if _PATTERN.fullmatch(value) is None:
            raise ValueError("policy name must be 1 to 64 letters, digits, underscores or hyphens")
        return value
