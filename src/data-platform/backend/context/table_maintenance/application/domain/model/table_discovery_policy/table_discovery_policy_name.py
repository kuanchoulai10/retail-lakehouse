"""Define the TableDiscoveryPolicyName value object."""

from __future__ import annotations

from pydantic import field_validator

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import checked_policy_name


class TableDiscoveryPolicyName(ValueObject):
    """Name a TableDiscoveryPolicy for display and URLs: 1 to 64 letters, digits, ``_`` or ``-``.

    Names are unique among discovery policies, but a policy is identified by its
    ``TableDiscoveryPolicyId``. A name shaped like a prefixed id is refused, so a name in a URL or a
    record can never be mistaken for an id.
    """

    value: str

    @field_validator("value")
    @classmethod
    def _matches_pattern(cls, value: str) -> str:
        return checked_policy_name(value)
