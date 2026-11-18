"""Define the AttachTableMaintenancePolicyUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class AttachTableMaintenancePolicyUseCaseInput(UseCaseInput):
    """Carry the request to attach a maintenance policy to a catalog, namespace or table."""

    target_type: str
    path: tuple[str, ...]
    policy_name: str
