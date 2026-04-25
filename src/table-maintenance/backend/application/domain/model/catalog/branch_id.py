"""Define the BranchId value object."""

from __future__ import annotations

from dataclasses import dataclass

from core.base.entity_id import EntityId


@dataclass(frozen=True)
class BranchId(EntityId):
    """Typed identifier for a Branch entity — the branch name."""
