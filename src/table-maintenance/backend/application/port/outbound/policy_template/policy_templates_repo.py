"""Define the PolicyTemplatesRepo outbound port."""

from __future__ import annotations

from abc import abstractmethod

from application.domain.model.policy_template.policy_template import PolicyTemplate
from base.entity_id import EntityId
from base.repository import Repository


class PolicyTemplatesRepo(Repository[PolicyTemplate]):
    """Persist and query PolicyTemplate aggregates."""

    @abstractmethod
    def update(self, template: PolicyTemplate) -> PolicyTemplate:
        """Persist the changed template and return it."""

    @abstractmethod
    def delete(self, entity_id: EntityId) -> None:
        """Delete the template with the given id."""

    @abstractmethod
    def find_by_name(self, name: str) -> PolicyTemplate | None:
        """Return the template with exactly this name, or None."""
