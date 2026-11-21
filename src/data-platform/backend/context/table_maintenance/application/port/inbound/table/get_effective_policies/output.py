"""Define the GetEffectivePoliciesUseCaseOutput."""

from __future__ import annotations

from typing import Any, Literal

from base import UseCaseOutput


class GetEffectivePoliciesUseCaseOutput(UseCaseOutput):
    """Carry the policy of each kind that applies, the level it applies from and the attachment it comes through.

    ``version`` is the policy's latest version, since an attachment always means it. ``target`` is
    ``{"type", "path", ["table_uuid"]}`` of the nearest attachment, and ``attachment_id`` its ``pa-`` or
    ``da-`` id; both are None when nothing is attached and the platform default applies.
    """

    class MaintenanceEntry(UseCaseOutput):
        """The maintenance policy that applies; ``dry_run`` when it plans without running."""

        policy_id: str
        policy_name: str
        version: int
        description: str
        dry_run: bool
        target: dict[str, Any] | None
        attachment_id: str | None

    class DiscoveryEntry(UseCaseOutput):
        """The discovery policy that applies; ``no_match_outcome`` decides a table no rule matches."""

        policy_id: str
        policy_name: str
        version: int
        description: str
        no_match_outcome: Literal["manage", "unmanage"]
        target: dict[str, Any] | None
        attachment_id: str | None

    maintenance: MaintenanceEntry
    discovery: DiscoveryEntry
