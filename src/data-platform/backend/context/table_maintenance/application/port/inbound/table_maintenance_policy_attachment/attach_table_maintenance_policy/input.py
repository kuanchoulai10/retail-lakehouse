"""Define the AttachTableMaintenancePolicyUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AttachTableMaintenancePolicyUseCaseInput:
    """Carry the request to attach a maintenance policy to a catalog, namespace or table."""

    target_type: str
    path: tuple[str, ...]
    policy_name: str
