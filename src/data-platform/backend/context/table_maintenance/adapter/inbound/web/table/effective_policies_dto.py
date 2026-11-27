"""Define the effective-policies API DTOs: one entry per kind of policy, told apart by ``kind``."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from context.table_maintenance.adapter.inbound.web.shared import PolicyTargetApiResponse


class MaintenanceEffectivePolicyApiResponse(BaseModel):
    """Describe the maintenance policy that applies, at its latest version, and the level it applies from.

    ``target`` is the nearest catalog, namespace or table holding a maintenance policy; it is null when
    none holds one and the platform default applies.
    """

    kind: Literal["maintenance"]
    policy_id: str
    policy_name: str
    version: int
    description: str
    dry_run: bool
    target: PolicyTargetApiResponse | None


class DiscoveryEffectivePolicyApiResponse(BaseModel):
    """Describe the discovery policy that applies, at its latest version, and the level it applies from.

    ``target`` is the nearest catalog, namespace or table holding a discovery policy. When none holds one
    no discovery policy applies, the place's tables are not managed, and every field but ``kind`` is
    null: there is no discovery default.
    """

    kind: Literal["discovery"]
    policy_id: str | None
    policy_name: str | None
    version: int | None
    description: str | None
    target: PolicyTargetApiResponse | None


class EffectivePoliciesApiResponse(BaseModel):
    """List the policy of each kind that applies: maintenance first, then discovery."""

    policies: list[
        Annotated[
            MaintenanceEffectivePolicyApiResponse | DiscoveryEffectivePolicyApiResponse,
            Field(discriminator="kind"),
        ]
    ]
