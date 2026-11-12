"""Define the AppliedPolicyRef value object."""

from __future__ import annotations

from typing import Any

from base import ValueObject


class AppliedPolicyRef(ValueObject):
    """Name the maintenance policy that applied to a table: its name, version and the target it is attached to.

    ``target`` is None for the platform default policy, which is attached to nothing.
    """

    name: str
    version: int
    target: dict[str, Any] | None = None
