"""Define the TableMaintenancePolicyName value object."""

from __future__ import annotations

import re

from pydantic import field_validator

from base import ValueObject

_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_PREFIXED_ID = re.compile(r"^[a-z]{2,8}-[0-7][0-9a-hjkmnp-tv-z]{25}$")


class TableMaintenancePolicyName(ValueObject):
    """Name a TableMaintenancePolicy for display and URLs: 1 to 64 letters, digits, ``_`` or ``-``.

    Names are unique, but a policy is identified by its ``TableMaintenancePolicyId``. A name shaped
    like a prefixed id (``mp-…`` or any other prefix, ADR 0011) is refused, so a name in a URL or a
    record can never be mistaken for an id.
    """

    value: str

    @field_validator("value")
    @classmethod
    def _matches_pattern(cls, value: str) -> str:
        if _PATTERN.fullmatch(value) is None:
            raise ValueError("policy name must be 1 to 64 letters, digits, underscores or hyphens")
        if _PREFIXED_ID.fullmatch(value) is not None:
            raise ValueError(
                "policy name must not look like a prefixed id (<prefix>-<26 base32 characters>); choose another name"
            )
        return value
