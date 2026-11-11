"""Define the TableMaintenancePoliciesSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError

from context.table_maintenance.adapter.outbound.table_maintenance_policy.sql.table_maintenance_policies_table import (
    table_maintenance_policies_table as policies,
)
from context.table_maintenance.adapter.outbound.table_maintenance_policy.sql.table_maintenance_policy_row_mapper import (  # noqa: E501
    TableMaintenancePolicyRowMapper,
)
from context.table_maintenance.adapter.outbound.table_maintenance_policy.sql.table_maintenance_policy_versions_table import (  # noqa: E501
    table_maintenance_policy_versions_table as versions,
)
from context.table_maintenance.application.exceptions import ConflictError
from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
    StalePolicyVersion,
    TableMaintenancePoliciesRepo,
)

if TYPE_CHECKING:
    from sqlalchemy import Connection, Engine

    from base import EntityId
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePolicy,
        TableMaintenancePolicyName,
        TableMaintenancePolicyVersion,
    )


class TableMaintenancePoliciesSqlRepo(TableMaintenancePoliciesRepo):
    """Store TableMaintenancePolicy aggregates and their versions in a SQL database."""

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: TableMaintenancePolicy) -> TableMaintenancePolicy:
        """Insert a new policy with its first version; a duplicate name raises ConflictError."""
        try:
            with self._engine.begin() as conn:
                conn.execute(insert(policies).values(**TableMaintenancePolicyRowMapper.to_policy_values(entity)))
                self._insert_version(conn, entity)
        except IntegrityError as exc:
            raise ConflictError(str(exc.orig)) from exc
        return entity

    def get(self, entity_id: EntityId) -> TableMaintenancePolicy | None:
        """Return the policy with the given name at its current version, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(select(policies).where(policies.c.name == entity_id.value)).first()
            if row is None:
                return None
            version_row = conn.execute(
                select(versions).where(versions.c.name == row.name, versions.c.version == row.version)
            ).one()
        return TableMaintenancePolicyRowMapper.to_aggregate(row._mapping, version_row._mapping)

    def list_all(self) -> list[TableMaintenancePolicy]:
        """Return all policies at their current version, ordered by name."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(policies, versions.c.content_json)
                .join(versions, (versions.c.name == policies.c.name) & (versions.c.version == policies.c.version))
                .order_by(policies.c.name)
            ).all()
        return [TableMaintenancePolicyRowMapper.to_aggregate(r._mapping, r._mapping) for r in rows]

    def update(self, policy: TableMaintenancePolicy) -> TableMaintenancePolicy:
        """Persist the replaced policy and its new version row in one transaction."""
        values = TableMaintenancePolicyRowMapper.to_policy_values(policy)
        with self._engine.begin() as conn:
            result = conn.execute(
                update(policies)
                .where(policies.c.name == policy.id.value, policies.c.version == policy.version - 1)
                .values(**values)
            )
            if result.rowcount == 0:
                if conn.execute(select(policies.c.name).where(policies.c.name == policy.id.value)).first() is None:
                    raise LookupError(f"table maintenance policy {policy.id.value} does not exist")
                raise StalePolicyVersion(f"policy {policy.id.value} was changed concurrently")
            self._insert_version(conn, policy)
        return policy

    def get_version(self, name: TableMaintenancePolicyName, version: int) -> TableMaintenancePolicyVersion | None:
        """Return one version of a policy, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(
                select(versions).where(versions.c.name == name.value, versions.c.version == version)
            ).first()
        return None if row is None else TableMaintenancePolicyRowMapper.to_version(row._mapping)

    def delete(self, entity_id: EntityId) -> None:
        """Delete the policy and all its versions."""
        with self._engine.begin() as conn:
            conn.execute(delete(versions).where(versions.c.name == entity_id.value))
            conn.execute(delete(policies).where(policies.c.name == entity_id.value))

    @staticmethod
    def _insert_version(conn: Connection, policy: TableMaintenancePolicy) -> None:
        conn.execute(
            insert(versions).values(**TableMaintenancePolicyRowMapper.to_version_values(policy.current_version()))
        )
