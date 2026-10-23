"""Define the DeletePolicyTemplateUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeletePolicyTemplateUseCaseInput:
    """Carry the request to delete a policy template that no rule references."""

    id: str
