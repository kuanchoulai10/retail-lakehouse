"""Define the GetEffectivePoliciesUseCaseOutput."""

from __future__ import annotations

from typing import Any

from base import UseCaseOutput


class GetEffectivePoliciesUseCaseOutput(UseCaseOutput):
    """Carry the policy of each kind that applies and the level it applies from.

    ``version`` is the policy's latest version, since attaching a policy always means its latest.
    ``target`` is ``{"type", "path", ["table_uuid"]}`` of the nearest place holding a policy of the
    kind, None when no place holds one. Then maintenance falls back to its platform default, while
    discovery has none: no discovery policy applies and every discovery field is None.
    """

    class MaintenanceEntry(UseCaseOutput):
        """The maintenance policy that applies; ``dry_run`` when it plans without running."""

        policy_id: str
        policy_name: str
        version: int
        description: str
        dry_run: bool
        target: dict[str, Any] | None

    class DiscoveryEntry(UseCaseOutput):
        """The discovery policy that applies, every field None when none does."""

        policy_id: str | None
        policy_name: str | None
        version: int | None
        description: str | None
        target: dict[str, Any] | None

    maintenance: MaintenanceEntry
    discovery: DiscoveryEntry
