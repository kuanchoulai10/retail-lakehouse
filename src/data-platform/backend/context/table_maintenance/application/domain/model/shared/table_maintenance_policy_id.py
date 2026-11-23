"""Define the TableMaintenancePolicyId identifier."""

from __future__ import annotations

from typing import ClassVar

from base import EntityId


class TableMaintenancePolicyId(EntityId):
    """Identify a TableMaintenancePolicy: a random ``mp-`` id minted when the policy is created (docs/adr/0011).

    Every relation to a policy is by this id; the policy's name is for display and URLs only.
    """

    PREFIX: ClassVar[str | None] = "mp"
