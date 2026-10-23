"""Define the InMemoryPolicyTemplatesRepo fake."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.exceptions import ConflictError
from application.port.outbound.policy_template.policy_templates_repo import (
    PolicyTemplatesRepo,
)

if TYPE_CHECKING:
    from application.domain.model.policy_template.policy_template import PolicyTemplate
    from base.entity_id import EntityId


class InMemoryPolicyTemplatesRepo(PolicyTemplatesRepo):
    """Keep templates in a dict, enforcing unique names like the SQL repo."""

    def __init__(self) -> None:
        """Start empty."""
        self.items: dict[str, PolicyTemplate] = {}

    def create(self, entity: PolicyTemplate) -> PolicyTemplate:
        """Insert a template; a duplicate name raises ConflictError."""
        if any(t.name == entity.name for t in self.items.values()):
            raise ConflictError(f"template name {entity.name!r} exists")
        self.items[entity.id.value] = entity
        return entity

    def get(self, entity_id: EntityId) -> PolicyTemplate | None:
        """Return the template or None."""
        return self.items.get(entity_id.value)

    def list_all(self) -> list[PolicyTemplate]:
        """Return templates ordered by name."""
        return sorted(self.items.values(), key=lambda t: t.name)

    def update(self, template: PolicyTemplate) -> PolicyTemplate:
        """Replace a stored template."""
        if template.id.value not in self.items:
            raise LookupError(f"policy template {template.id.value} does not exist")
        self.items[template.id.value] = template
        return template

    def delete(self, entity_id: EntityId) -> None:
        """Remove a template if present."""
        self.items.pop(entity_id.value, None)

    def find_by_name(self, name: str) -> PolicyTemplate | None:
        """Return the template with this exact name."""
        return next((t for t in self.items.values() if t.name == name), None)
