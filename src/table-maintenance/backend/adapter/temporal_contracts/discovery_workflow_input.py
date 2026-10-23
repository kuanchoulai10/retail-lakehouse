"""Define the DiscoveryWorkflowInput workflow contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DiscoveryWorkflowInput:
    """Scope a discovery run to a catalog or one namespace."""

    catalog: str
    namespace: str | None = None
