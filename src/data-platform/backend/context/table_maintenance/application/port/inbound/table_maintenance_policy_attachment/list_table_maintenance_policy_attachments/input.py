"""Define the ListTableMaintenancePolicyAttachmentsUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class ListTableMaintenancePolicyAttachmentsUseCaseInput(UseCaseInput):
    """Carry the request to list attachments, optionally of one policy."""

    policy_name: str | None = None
