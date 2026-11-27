"""Define the ManagementDecision value object."""

from __future__ import annotations

from typing import Self

from pydantic import model_validator

from base import ValueObject
from context.table_maintenance.application.domain.model.table_discovery_policy.decision.decided_by import DecidedBy


class ManagementDecision(ValueObject):
    """What discovery decided for a table, and what decided it.

    ``decided_by`` is None only when no discovery policy applies, which manages nothing.
    """

    manage: bool
    decided_by: DecidedBy | None

    @model_validator(mode="after")
    def _managing_names_its_decider(self) -> Self:
        if self.manage and self.decided_by is None:
            raise ValueError("a table is managed only because a discovery policy decided it")
        return self

    @classmethod
    def nothing_attached(cls) -> ManagementDecision:
        """Return the decision when no discovery policy applies: manage nothing, decided by nothing."""
        return cls(manage=False, decided_by=None)
