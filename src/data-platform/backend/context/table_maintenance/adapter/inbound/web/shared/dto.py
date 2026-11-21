"""Define the policy target API DTOs, shared by every kind of policy attachment.

A target is ``{"type", "path"}`` as in Polaris's policy mappings, with the catalog as the first path
element because this API is not scoped to one catalog: ``[catalog]``, ``[catalog, ns1, ...]`` or
``[catalog, ns1, ..., table]``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

PolicyTargetKind = Literal["catalog", "namespace", "table"]


class PolicyTargetApiRequest(BaseModel):
    """Name a catalog, namespace or table to attach a policy to."""

    model_config = ConfigDict(extra="forbid")

    type: PolicyTargetKind
    path: list[str]


class DetachPolicyTargetApiRequest(BaseModel):
    """Name the target to detach from; a table no longer in the catalog is named by its ``table_uuid``."""

    model_config = ConfigDict(extra="forbid")

    type: PolicyTargetKind
    path: list[str]
    table_uuid: str | None = None


class PolicyTargetApiResponse(BaseModel):
    """Describe a target; a table target carries the uuid it is keyed by."""

    type: str
    path: list[str]
    table_uuid: str | None
