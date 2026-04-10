from dataclasses import dataclass

from base.entity_id import EntityId


@dataclass(frozen=True)
class JobId(EntityId):
    """Typed identifier for a Job aggregate."""
