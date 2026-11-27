"""Define the raise_place_write_refused function."""

from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn

from context.table_maintenance.adapter.outbound.shared.sql.integrity_violation import IntegrityViolation
from context.table_maintenance.adapter.outbound.shared.sql.integrity_violation_of import integrity_violation_of
from context.table_maintenance.application.exceptions import ConcurrentUpdateError, ConflictError

if TYPE_CHECKING:
    from sqlalchemy.exc import IntegrityError

    from base import EntityId


def raise_place_write_refused(
    error: IntegrityError,
    place: str,
    *,
    discovery_policy_id: EntityId | None,
    maintenance_policy_id: EntityId | None,
) -> NoReturn:
    """Raise the application error for a refused write of a catalog, namespace or table, in plain words.

    ``place`` describes the row (``catalog iceberg``). A duplicate key means another writer stored the
    place first, a lost race worth retrying: ``ConcurrentUpdateError``. A missing foreign key means a
    policy the place holds was deleted since it was read: ``ConflictError`` naming the policies it
    holds. No database text reaches either message. Any other refusal is a server bug and is raised
    as it is.
    """
    kind = integrity_violation_of(error)
    if kind == IntegrityViolation.UNIQUE:
        raise ConcurrentUpdateError(f"{place} was changed by someone else") from error
    if kind == IntegrityViolation.FOREIGN_KEY:
        held = [
            f"{policy_kind} policy {policy_id.value}"
            for policy_kind, policy_id in (("discovery", discovery_policy_id), ("maintenance", maintenance_policy_id))
            if policy_id is not None
        ]
        raise ConflictError(f"{' or '.join(held) or 'a policy'} held by {place} no longer exists") from error
    raise error
