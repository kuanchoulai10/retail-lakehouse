"""Define the JobRunId value object."""

from dataclasses import dataclass

from base.entity_id import EntityId


@dataclass(frozen=True)
class JobRunId(EntityId):
    """Typed identifier for a JobRun aggregate."""
