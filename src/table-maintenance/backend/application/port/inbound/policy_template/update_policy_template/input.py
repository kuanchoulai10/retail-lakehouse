"""Define the UpdatePolicyTemplateUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class UpdatePolicyTemplateUseCaseInput:
    """Carry the request to rename a policy template or replace its settings."""

    id: str
    name: str | None = None
    settings: dict[str, Any] | None = None
