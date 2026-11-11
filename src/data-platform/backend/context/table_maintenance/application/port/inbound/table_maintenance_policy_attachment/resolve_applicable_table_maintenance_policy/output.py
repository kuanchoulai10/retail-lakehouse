"""Define the ResolveApplicableTableMaintenancePolicyUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


@dataclass(frozen=True)
class ResolveApplicableTableMaintenancePolicyUseCaseOutput:
    """Carry the outcome of the request."""

    policy_name: str
    version: int
    content: dict[str, Any]
    target: dict[str, Any] | None
