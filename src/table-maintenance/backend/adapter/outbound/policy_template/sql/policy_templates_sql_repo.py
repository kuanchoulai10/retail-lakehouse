"""Define the PolicyTemplatesSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, insert, select, update

from adapter.outbound.policy_template.sql.policy_template_row_mapper import (
    PolicyTemplateRowMapper,
)
from adapter.outbound.policy_template.sql.policy_templates_table import (
    policy_templates_table as t,
)
from application.port.outbound.policy_template.policy_templates_repo import (
    PolicyTemplatesRepo,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from application.domain.model.policy_template.policy_template import PolicyTemplate
    from base.entity_id import EntityId


class PolicyTemplatesSqlRepo(PolicyTemplatesRepo):
    """Store PolicyTemplate aggregates in a SQL database."""

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: PolicyTemplate) -> PolicyTemplate:
        """Insert a new template; a duplicate name raises IntegrityError."""
        with self._engine.begin() as conn:
            conn.execute(insert(t).values(**PolicyTemplateRowMapper.to_values(entity)))
        return entity

    def get(self, entity_id: EntityId) -> PolicyTemplate | None:
        """Return the template with the given id, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(select(t).where(t.c.id == entity_id.value)).first()
        return (
            None if row is None else PolicyTemplateRowMapper.to_aggregate(row._mapping)
        )

    def list_all(self) -> list[PolicyTemplate]:
        """Return all templates ordered by name."""
        with self._engine.connect() as conn:
            rows = conn.execute(select(t).order_by(t.c.name)).all()
        return [PolicyTemplateRowMapper.to_aggregate(r._mapping) for r in rows]

    def update(self, template: PolicyTemplate) -> PolicyTemplate:
        """Persist the changed template."""
        values = PolicyTemplateRowMapper.to_values(template)
        with self._engine.begin() as conn:
            result = conn.execute(
                update(t).where(t.c.id == template.id.value).values(**values)
            )
        if result.rowcount == 0:
            raise LookupError(f"policy template {template.id.value} does not exist")
        return template

    def delete(self, entity_id: EntityId) -> None:
        """Delete the template with the given id."""
        with self._engine.begin() as conn:
            conn.execute(delete(t).where(t.c.id == entity_id.value))

    def find_by_name(self, name: str) -> PolicyTemplate | None:
        """Return the template with exactly this name, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(select(t).where(t.c.name == name)).first()
        return (
            None if row is None else PolicyTemplateRowMapper.to_aggregate(row._mapping)
        )
