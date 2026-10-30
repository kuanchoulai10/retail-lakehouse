"""Define the TableDiscoveryWorkflowInput workflow contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableDiscoveryWorkflowInput:
    """Scope a discovery run to a catalog or one namespace."""

    catalog: str
    namespace: str | None = None
