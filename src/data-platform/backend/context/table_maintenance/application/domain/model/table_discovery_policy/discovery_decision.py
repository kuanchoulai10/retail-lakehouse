"""Define the DiscoveryDecision value object."""

from __future__ import annotations

from base import ValueObject
from context.table_maintenance.application.domain.model.table_discovery_policy.discovery_match import (
    DiscoveryMatch,
)
from context.table_maintenance.application.domain.model.table_discovery_policy.discovery_outcome import (
    DiscoveryOutcome,
)


class DiscoveryDecision(ValueObject):
    """What a discovery policy decided for a table, and what decided it."""

    outcome: DiscoveryOutcome
    match: DiscoveryMatch

    @property
    def manages(self) -> bool:
        """Return whether the table is to be managed."""
        return self.outcome is DiscoveryOutcome.MANAGE
