"""Define the ListTableDiscoveryPolicyAttachmentsUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class ListTableDiscoveryPolicyAttachmentsUseCaseInput(UseCaseInput):
    """Carry the request to list one discovery policy's attachments."""

    policy_name: str
