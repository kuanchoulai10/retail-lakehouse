"""Define the PolicyTemplateId identifier."""

from __future__ import annotations

from dataclasses import dataclass

from base.entity_id import EntityId


@dataclass(frozen=True)
class PolicyTemplateId(EntityId):
    """Identify a PolicyTemplate."""
