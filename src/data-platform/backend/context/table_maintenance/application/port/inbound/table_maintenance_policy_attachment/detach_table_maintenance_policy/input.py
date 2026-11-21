"""Define the DetachTableMaintenancePolicyUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class DetachTableMaintenancePolicyUseCaseInput(UseCaseInput):
    """Carry the request to detach the attachment ``attachment_id`` (a ``pa-`` id) of the policy ``policy_name``."""

    policy_name: str
    attachment_id: str
