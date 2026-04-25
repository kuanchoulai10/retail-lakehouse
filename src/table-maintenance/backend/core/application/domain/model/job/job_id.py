"""Define the JobId value object."""

from dataclasses import dataclass

from core.base.entity_id import EntityId


@dataclass(frozen=True)
class JobId(EntityId):
    """Typed identifier for a Job aggregate."""
