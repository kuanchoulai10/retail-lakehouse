"""Define the TableDiscoveryPoliciesSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError

from context.table_maintenance.adapter.outbound.table_discovery_policy.sql.table_discovery_policies_table import (
    table_discovery_policies_table as policies,
)
from context.table_maintenance.adapter.outbound.table_discovery_policy.sql.table_discovery_policy_row_mapper import (  # noqa: E501
    TableDiscoveryPolicyRowMapper,
)
from context.table_maintenance.adapter.outbound.table_discovery_policy.sql.table_discovery_policy_versions_table import (  # noqa: E501
    table_discovery_policy_versions_table as versions,
)
from context.table_maintenance.application.exceptions import ConflictError
from context.table_maintenance.application.port.outbound.table_discovery_policy import (
    StaleDiscoveryPolicyVersion,
    TableDiscoveryPoliciesRepo,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy import ColumnElement, Connection, Engine

    from base import EntityId
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPolicy,
        TableDiscoveryPolicyName,
        TableDiscoveryPolicyVersion,
    )


class TableDiscoveryPoliciesSqlRepo(TableDiscoveryPoliciesRepo):
    """Store TableDiscoveryPolicy aggregates and their versions in a SQL database.

    A policy row is keyed by its ``dp-`` id and its versions by ``(policy_id, version)``; the
    unique index on ``name`` keeps names unique, so a second policy with a taken name is
    refused with ConflictError. An attachment's foreign key to the policy refuses its delete.
    """

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: TableDiscoveryPolicy) -> TableDiscoveryPolicy:
        """Insert a new policy with its first version; a taken id or name raises ConflictError."""
        try:
            with self._engine.begin() as conn:
                conn.execute(insert(policies).values(**TableDiscoveryPolicyRowMapper.to_policy_values(entity)))
                self._insert_version(conn, entity)
        except IntegrityError as exc:
            raise ConflictError(str(exc.orig)) from exc
        return entity

    def get(self, entity_id: EntityId) -> TableDiscoveryPolicy | None:
        """Return the policy with the given id at its current version, or None."""
        found = self._current(policies.c.id == entity_id.value)
        return found[0] if found else None

    def get_by_name(self, name: TableDiscoveryPolicyName) -> TableDiscoveryPolicy | None:
        """Return the policy with the given name at its current version, or None."""
        found = self._current(policies.c.name == name.value)
        return found[0] if found else None

    def get_many(self, ids: Sequence[EntityId]) -> list[TableDiscoveryPolicy]:
        """Return the policies that exist among the ids, at their current version."""
        return self._current(policies.c.id.in_([i.value for i in ids]))

    def list_all(self) -> list[TableDiscoveryPolicy]:
        """Return all policies at their current version, ordered by name."""
        return self._current(None)

    def update(self, policy: TableDiscoveryPolicy) -> TableDiscoveryPolicy:
        """Persist the replaced policy and its new version row in one transaction.

        The row is updated only while it is still at ``policy.version - 1``, so of two writers
        replacing the same version the second raises StaleDiscoveryPolicyVersion.
        """
        values = TableDiscoveryPolicyRowMapper.to_policy_values(policy)
        with self._engine.begin() as conn:
            result = conn.execute(
                update(policies)
                .where(policies.c.id == policy.id.value, policies.c.version == policy.version - 1)
                .values(**values)
            )
            if result.rowcount == 0:
                if conn.execute(select(policies.c.id).where(policies.c.id == policy.id.value)).first() is None:
                    raise LookupError(f"table discovery policy {policy.id.value} does not exist")
                raise StaleDiscoveryPolicyVersion(f"discovery policy {policy.name.value} was changed concurrently")
            self._insert_version(conn, policy)
        return policy

    def get_version(self, policy_id: EntityId, version: int) -> TableDiscoveryPolicyVersion | None:
        """Return one version of a policy, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(
                select(versions).where(versions.c.policy_id == policy_id.value, versions.c.version == version)
            ).first()
        return None if row is None else TableDiscoveryPolicyRowMapper.to_version(row._mapping)

    def delete(self, entity_id: EntityId) -> None:
        """Delete the policy and all its versions; one attached meanwhile raises ConflictError and stays."""
        try:
            with self._engine.begin() as conn:
                conn.execute(delete(versions).where(versions.c.policy_id == entity_id.value))
                conn.execute(delete(policies).where(policies.c.id == entity_id.value))
        except IntegrityError as exc:
            raise ConflictError(
                f"discovery policy {entity_id.value} is still attached to a catalog, namespace or table"
            ) from exc

    def _current(self, where: ColumnElement[bool] | None) -> list[TableDiscoveryPolicy]:
        """Return the policies matching ``where`` (all when None) at their current version, ordered by name."""
        statement = select(policies, versions.c.content_json).join(
            versions, (versions.c.policy_id == policies.c.id) & (versions.c.version == policies.c.version)
        )
        if where is not None:
            statement = statement.where(where)
        with self._engine.connect() as conn:
            rows = conn.execute(statement.order_by(policies.c.name)).all()
        return [TableDiscoveryPolicyRowMapper.to_aggregate(r._mapping, r._mapping) for r in rows]

    @staticmethod
    def _insert_version(conn: Connection, policy: TableDiscoveryPolicy) -> None:
        conn.execute(
            insert(versions).values(**TableDiscoveryPolicyRowMapper.to_version_values(policy.current_version()))
        )
