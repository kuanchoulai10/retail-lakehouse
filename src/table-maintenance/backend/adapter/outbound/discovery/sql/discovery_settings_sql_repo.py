"""Define the DiscoverySettingsSqlRepo."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

from adapter.outbound.discovery.sql.discovery_settings_table import (
    discovery_settings_table as t,
)
from application.domain.model.discovery.discovery_settings import (
    GLOBAL_ID,
    DiscoverySettings,
)
from application.domain.model.discovery.discovery_settings_id import (
    DiscoverySettingsId,
)
from application.exceptions import ConflictError
from application.port.outbound.discovery.discovery_settings_repo import (
    DiscoverySettingsRepo,
)

if TYPE_CHECKING:
    from sqlalchemy import RowMapping

    from sqlalchemy import Engine

    from base.entity_id import EntityId


def _to_values(settings: DiscoverySettings) -> dict[str, Any]:
    return {
        "id": settings.id.value,
        "enabled": settings.enabled,
        "updated_at": settings.updated_at,
    }


def _to_aggregate(row: RowMapping) -> DiscoverySettings:
    return DiscoverySettings(
        id=DiscoverySettingsId(row["id"]),
        enabled=row["enabled"],
        updated_at=row["updated_at"],
    )


class DiscoverySettingsSqlRepo(DiscoverySettingsRepo):
    """Store the singleton DiscoverySettings in a SQL database."""

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: DiscoverySettings) -> DiscoverySettings:
        """Insert new settings."""
        try:
            with self._engine.begin() as conn:
                conn.execute(insert(t).values(**_to_values(entity)))
        except IntegrityError as exc:
            raise ConflictError(str(exc.orig)) from exc
        return entity

    def get(self, entity_id: EntityId) -> DiscoverySettings | None:
        """Return the settings with the given id, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(select(t).where(t.c.id == entity_id.value)).first()
        return None if row is None else _to_aggregate(row._mapping)

    def list_all(self) -> list[DiscoverySettings]:
        """Return all stored settings."""
        with self._engine.connect() as conn:
            rows = conn.execute(select(t).order_by(t.c.id)).all()
        return [_to_aggregate(r._mapping) for r in rows]

    def get_settings(self) -> DiscoverySettings:
        """Return the singleton settings, enabled by default when absent."""
        found = self.get(GLOBAL_ID)
        if found is not None:
            return found
        return DiscoverySettings.create(datetime.now(UTC), enabled=True)

    def save(self, settings: DiscoverySettings) -> None:
        """Insert or replace the singleton settings."""
        values = _to_values(settings)
        with self._engine.begin() as conn:
            result = conn.execute(
                update(t).where(t.c.id == settings.id.value).values(**values)
            )
            if result.rowcount == 0:
                conn.execute(insert(t).values(**values))
