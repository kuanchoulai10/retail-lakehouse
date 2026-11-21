"""Define the TableDiscoveryPolicyAttachmentsSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError

from context.table_maintenance.adapter.outbound.table_discovery_policy_attachment.sql.table_discovery_policy_attachment_row_mapper import (  # noqa: E501
    TableDiscoveryPolicyAttachmentRowMapper,
)
from context.table_maintenance.adapter.outbound.table_discovery_policy_attachment.sql.table_discovery_policy_attachments_table import (  # noqa: E501
    table_discovery_policy_attachments_table as attachments,
)
from context.table_maintenance.application.exceptions import ConflictError
from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
    TableDiscoveryPolicyAttachmentsRepo,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy import Engine, Select

    from base import EntityId
    from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
        PolicyTarget,
        TableDiscoveryPolicyAttachment,
        TableDiscoveryPolicyId,
    )


class TableDiscoveryPolicyAttachmentsSqlRepo(TableDiscoveryPolicyAttachmentsRepo):
    """Store TableDiscoveryPolicyAttachment aggregates in a SQL database.

    An attachment's id is random; the unique index on ``target_key`` keeps one
    attachment per target, so two attaches to one target at once collide there
    and the second is refused with ConflictError. The indexed ``catalog`` column
    lets a scan read only its catalog's attachments.
    """

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: TableDiscoveryPolicyAttachment) -> TableDiscoveryPolicyAttachment:
        """Insert an attachment; a second one on the same target, or an unknown policy, raises ConflictError."""
        try:
            with self._engine.begin() as conn:
                conn.execute(insert(attachments).values(**TableDiscoveryPolicyAttachmentRowMapper.to_values(entity)))
        except IntegrityError as exc:
            raise ConflictError(str(exc.orig)) from exc
        return entity

    def get(self, entity_id: EntityId) -> TableDiscoveryPolicyAttachment | None:
        """Return the attachment with the given id, or None."""
        found = self._select(select(attachments).where(attachments.c.id == entity_id.value))
        return found[0] if found else None

    def get_by_target(self, target: PolicyTarget) -> TableDiscoveryPolicyAttachment | None:
        """Return the attachment on the target, matched by its key, or None."""
        found = self._select(select(attachments).where(attachments.c.target_key == target.key()))
        return found[0] if found else None

    def get_many_by_targets(self, targets: Sequence[PolicyTarget]) -> list[TableDiscoveryPolicyAttachment]:
        """Return the attachments on any of the targets, matched by key."""
        return self._select(select(attachments).where(attachments.c.target_key.in_([t.key() for t in targets])))

    def list_in_catalog(self, catalog: str) -> list[TableDiscoveryPolicyAttachment]:
        """Return the attachments whose target is in the catalog, ordered by id."""
        return self._select(select(attachments).where(attachments.c.catalog == catalog).order_by(attachments.c.id))

    def list_all(self) -> list[TableDiscoveryPolicyAttachment]:
        """Return all attachments ordered by id."""
        return self._select(select(attachments).order_by(attachments.c.id))

    def list_for_policy(self, policy_id: TableDiscoveryPolicyId) -> list[TableDiscoveryPolicyAttachment]:
        """Return the attachments of one policy ordered by id."""
        return self._select(
            select(attachments).where(attachments.c.policy_id == policy_id.value).order_by(attachments.c.id)
        )

    def has_attachments_for_policy(self, policy_id: TableDiscoveryPolicyId) -> bool:
        """Return whether any attachment uses the policy."""
        with self._engine.connect() as conn:
            return (
                conn.execute(
                    select(attachments.c.id).where(attachments.c.policy_id == policy_id.value).limit(1)
                ).first()
                is not None
            )

    def update(self, attachment: TableDiscoveryPolicyAttachment) -> TableDiscoveryPolicyAttachment:
        """Persist the attachment's policy and time."""
        values = TableDiscoveryPolicyAttachmentRowMapper.to_values(attachment)
        with self._engine.begin() as conn:
            result = conn.execute(update(attachments).where(attachments.c.id == attachment.id.value).values(**values))
            if result.rowcount == 0:
                raise LookupError(f"discovery attachment {attachment.id.value} does not exist")
        return attachment

    def delete(self, entity_id: EntityId) -> None:
        """Delete the attachment if present."""
        with self._engine.begin() as conn:
            conn.execute(delete(attachments).where(attachments.c.id == entity_id.value))

    def _select(self, statement: Select) -> list[TableDiscoveryPolicyAttachment]:
        with self._engine.connect() as conn:
            rows = conn.execute(statement).all()
        return [TableDiscoveryPolicyAttachmentRowMapper.to_aggregate(r._mapping) for r in rows]
