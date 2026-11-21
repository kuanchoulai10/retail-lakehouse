"""Define the PolicyTargetType enum."""

from __future__ import annotations

from enum import StrEnum


class PolicyTargetType(StrEnum):
    """The kind of object a policy is attached to."""

    CATALOG = "catalog"
    NAMESPACE = "namespace"
    TABLE = "table"
