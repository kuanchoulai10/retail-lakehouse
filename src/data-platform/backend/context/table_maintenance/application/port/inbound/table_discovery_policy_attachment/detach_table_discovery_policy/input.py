"""Define the DetachTableDiscoveryPolicyUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class DetachTableDiscoveryPolicyUseCaseInput(UseCaseInput):
    """Carry the request to detach the attachment ``attachment_id`` (a ``da-`` id) of the policy ``policy_name``."""

    policy_name: str
    attachment_id: str
