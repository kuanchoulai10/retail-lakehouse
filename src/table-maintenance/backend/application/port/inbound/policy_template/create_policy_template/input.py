"""Define the CreatePolicyTemplateUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CreatePolicyTemplateUseCaseInput:
    """Carry the request to create a policy template."""

    name: str
    settings: dict[str, Any] = field(default_factory=dict)
