"""Define the ListTableMaintenancePolicyAttachmentsUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListTableMaintenancePolicyAttachmentsUseCaseInput:
    """Carry the request to list attachments, optionally of one policy."""

    policy_name: str | None = None
