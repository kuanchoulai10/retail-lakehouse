"""Define the TableMaintenancePolicyName value object."""

from __future__ import annotations

import re

from pydantic import field_validator

from base import ValueObject

_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class TableMaintenancePolicyName(ValueObject):
    """Name a TableMaintenancePolicy for display and URLs: 1 to 64 letters, digits, ``_`` or ``-``.

    Names are unique, but a policy is identified by its ``TableMaintenancePolicyId``.
    """

    value: str

    @field_validator("value")
    @classmethod
    def _matches_pattern(cls, value: str) -> str:
        if _PATTERN.fullmatch(value) is None:
            raise ValueError("policy name must be 1 to 64 letters, digits, underscores or hyphens")
        return value
