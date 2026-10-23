"""Define the GetPolicyTemplateUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetPolicyTemplateUseCaseInput:
    """Carry the request to get one policy template."""

    id: str
