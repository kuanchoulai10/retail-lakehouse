"""Define the effective-policies API DTOs: one entry per kind of policy, told apart by ``kind``."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from context.table_maintenance.adapter.inbound.web.shared import PolicyTargetApiResponse


class MaintenanceEffectivePolicyApiResponse(BaseModel):
    """Describe the maintenance policy that applies, at its latest version, and the level it applies from.

    ``target`` is the nearest attachment's target and ``attachment_id`` its ``pa-`` id; both are null when
    the platform default applies.
    """

    kind: Literal["maintenance"]
    policy_id: str
    policy_name: str
    version: int
    description: str
    dry_run: bool
    target: PolicyTargetApiResponse | None
    attachment_id: str | None


class DiscoveryEffectivePolicyApiResponse(BaseModel):
    """Describe the discovery policy that applies, at its latest version, and the level it applies from.

    ``target`` is the nearest attachment's target and ``attachment_id`` its ``da-`` id; both are null when
    the platform default applies.
    """

    kind: Literal["discovery"]
    policy_id: str
    policy_name: str
    version: int
    description: str
    no_match_outcome: Literal["manage", "unmanage"]
    target: PolicyTargetApiResponse | None
    attachment_id: str | None


class EffectivePoliciesApiResponse(BaseModel):
    """List the policy of each kind that applies: maintenance first, then discovery."""

    policies: list[
        Annotated[
            MaintenanceEffectivePolicyApiResponse | DiscoveryEffectivePolicyApiResponse,
            Field(discriminator="kind"),
        ]
    ]
