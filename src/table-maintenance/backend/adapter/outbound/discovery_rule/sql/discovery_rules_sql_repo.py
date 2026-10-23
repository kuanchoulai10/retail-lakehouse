"""Define the DiscoveryRulesSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError

from adapter.outbound.discovery_rule.sql.discovery_rule_row_mapper import (
    DiscoveryRuleRowMapper,
)
from adapter.outbound.discovery_rule.sql.discovery_rules_table import (
    discovery_rules_table as t,
)
from application.exceptions import ConflictError
from application.port.outbound.discovery_rule.discovery_rules_repo import (
    DiscoveryRulesRepo,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from application.domain.model.discovery_rule.discovery_rule import DiscoveryRule
    from application.domain.model.policy_template.policy_template_id import (
        PolicyTemplateId,
    )
    from base.entity_id import EntityId


class DiscoveryRulesSqlRepo(DiscoveryRulesRepo):
    """Store DiscoveryRule aggregates in a SQL database."""

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: DiscoveryRule) -> DiscoveryRule:
        """Insert a new rule."""
        try:
            with self._engine.begin() as conn:
                conn.execute(
                    insert(t).values(**DiscoveryRuleRowMapper.to_values(entity))
                )
        except IntegrityError as exc:
            raise ConflictError(str(exc.orig)) from exc
        return entity

    def get(self, entity_id: EntityId) -> DiscoveryRule | None:
        """Return the rule with the given id, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(select(t).where(t.c.id == entity_id.value)).first()
        return (
            None if row is None else DiscoveryRuleRowMapper.to_aggregate(row._mapping)
        )

    def list_all(self) -> list[DiscoveryRule]:
        """Return all rules ordered by (priority, id)."""
        with self._engine.connect() as conn:
            rows = conn.execute(select(t).order_by(t.c.priority, t.c.id)).all()
        return [DiscoveryRuleRowMapper.to_aggregate(r._mapping) for r in rows]

    def update(self, rule: DiscoveryRule) -> DiscoveryRule:
        """Persist the changed rule."""
        values = DiscoveryRuleRowMapper.to_values(rule)
        with self._engine.begin() as conn:
            result = conn.execute(
                update(t).where(t.c.id == rule.id.value).values(**values)
            )
            if result.rowcount == 0:
                raise LookupError(f"discovery rule {rule.id.value} does not exist")
        return rule

    def delete(self, entity_id: EntityId) -> None:
        """Delete the rule with the given id."""
        with self._engine.begin() as conn:
            conn.execute(delete(t).where(t.c.id == entity_id.value))

    def count_by_template(self, template_id: PolicyTemplateId) -> int:
        """Return how many rules reference the template."""
        stmt = (
            select(func.count())
            .select_from(t)
            .where(t.c.template_id == template_id.value)
        )
        with self._engine.connect() as conn:
            return int(conn.execute(stmt).scalar_one())
