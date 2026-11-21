"""Define the ListTableMaintenancePolicyAttachmentsUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class ListTableMaintenancePolicyAttachmentsUseCaseInput(UseCaseInput):
    """Carry the request to list one maintenance policy's attachments."""

    policy_name: str
