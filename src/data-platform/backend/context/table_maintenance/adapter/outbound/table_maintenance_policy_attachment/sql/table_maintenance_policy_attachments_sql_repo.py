"""Define the TableMaintenancePolicyAttachmentsSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError

from context.table_maintenance.adapter.outbound.table_maintenance_policy_attachment.sql.table_maintenance_policy_attachment_row_mapper import (  # noqa: E501
    TableMaintenancePolicyAttachmentRowMapper,
)
from context.table_maintenance.adapter.outbound.table_maintenance_policy_attachment.sql.table_maintenance_policy_attachments_table import (  # noqa: E501
    table_maintenance_policy_attachments_table as attachments,
)
from context.table_maintenance.application.exceptions import ConflictError
from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
    TableMaintenancePolicyAttachmentsRepo,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy import Engine

    from base import EntityId
    from context.table_maintenance.application.port.outbound.table_maintenance_policy_attachment import (
        TableMaintenancePolicyAttachment,
        TableMaintenancePolicyName,
    )


class TableMaintenancePolicyAttachmentsSqlRepo(TableMaintenancePolicyAttachmentsRepo):
    """Store TableMaintenancePolicyAttachment aggregates in a SQL database."""

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: TableMaintenancePolicyAttachment) -> TableMaintenancePolicyAttachment:
        """Insert an attachment; a second one on the same target raises ConflictError."""
        try:
            with self._engine.begin() as conn:
                conn.execute(insert(attachments).values(**TableMaintenancePolicyAttachmentRowMapper.to_values(entity)))
        except IntegrityError as exc:
            raise ConflictError(str(exc.orig)) from exc
        return entity

    def get(self, entity_id: EntityId) -> TableMaintenancePolicyAttachment | None:
        """Return the attachment with the given id, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(select(attachments).where(attachments.c.id == entity_id.value)).first()
        return None if row is None else TableMaintenancePolicyAttachmentRowMapper.to_aggregate(row._mapping)

    def list_all(self) -> list[TableMaintenancePolicyAttachment]:
        """Return all attachments ordered by id."""
        return self._select(select(attachments).order_by(attachments.c.id))

    def update(self, attachment: TableMaintenancePolicyAttachment) -> TableMaintenancePolicyAttachment:
        """Persist the attachment's policy and time."""
        values = TableMaintenancePolicyAttachmentRowMapper.to_values(attachment)
        with self._engine.begin() as conn:
            result = conn.execute(update(attachments).where(attachments.c.id == attachment.id.value).values(**values))
            if result.rowcount == 0:
                raise LookupError(f"attachment {attachment.id.value} does not exist")
        return attachment

    def delete(self, entity_id: EntityId) -> None:
        """Delete the attachment if present."""
        with self._engine.begin() as conn:
            conn.execute(delete(attachments).where(attachments.c.id == entity_id.value))

    def get_many(self, ids: Sequence[EntityId]) -> list[TableMaintenancePolicyAttachment]:
        """Return the attachments that exist among the ids."""
        return self._select(select(attachments).where(attachments.c.id.in_([i.value for i in ids])))

    def list_for_policy(self, policy_name: TableMaintenancePolicyName) -> list[TableMaintenancePolicyAttachment]:
        """Return the attachments of one policy ordered by id."""
        return self._select(
            select(attachments).where(attachments.c.policy_name == policy_name.value).order_by(attachments.c.id)
        )

    def has_attachments_for_policy(self, policy_name: TableMaintenancePolicyName) -> bool:
        """Return whether any attachment uses the policy."""
        with self._engine.connect() as conn:
            return (
                conn.execute(
                    select(attachments.c.id).where(attachments.c.policy_name == policy_name.value).limit(1)
                ).first()
                is not None
            )

    def _select(self, statement) -> list[TableMaintenancePolicyAttachment]:  # noqa: ANN001
        with self._engine.connect() as conn:
            rows = conn.execute(statement).all()
        return [TableMaintenancePolicyAttachmentRowMapper.to_aggregate(r._mapping) for r in rows]
