"""Define the TableMaintenancePresetsSqlRepo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError

from adapter.outbound.table_maintenance_preset.sql.table_maintenance_preset_row_mapper import (
    TableMaintenancePresetRowMapper,
)
from adapter.outbound.table_maintenance_preset.sql.table_maintenance_presets_table import (
    table_maintenance_presets_table as t,
)
from application.exceptions import ConflictError
from application.port.outbound.table_maintenance_preset import (
    TableMaintenancePresetsRepo,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from application.port.outbound.table_maintenance_preset import (
        TableMaintenancePreset,
    )
    from base import EntityId


class TableMaintenancePresetsSqlRepo(TableMaintenancePresetsRepo):
    """Store TableMaintenancePreset aggregates in a SQL database."""

    def __init__(self, engine: Engine) -> None:
        """Bind the repository to an engine."""
        self._engine = engine

    def create(self, entity: TableMaintenancePreset) -> TableMaintenancePreset:
        """Insert a new preset; a duplicate name raises IntegrityError."""
        try:
            with self._engine.begin() as conn:
                conn.execute(
                    insert(t).values(
                        **TableMaintenancePresetRowMapper.to_values(entity)
                    )
                )
        except IntegrityError as exc:
            raise ConflictError(str(exc.orig)) from exc
        return entity

    def get(self, entity_id: EntityId) -> TableMaintenancePreset | None:
        """Return the preset with the given id, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(select(t).where(t.c.id == entity_id.value)).first()
        return (
            None
            if row is None
            else TableMaintenancePresetRowMapper.to_aggregate(row._mapping)
        )

    def list_all(self) -> list[TableMaintenancePreset]:
        """Return all presets ordered by name."""
        with self._engine.connect() as conn:
            rows = conn.execute(select(t).order_by(t.c.name)).all()
        return [TableMaintenancePresetRowMapper.to_aggregate(r._mapping) for r in rows]

    def update(self, preset: TableMaintenancePreset) -> TableMaintenancePreset:
        """Persist the changed preset."""
        values = TableMaintenancePresetRowMapper.to_values(preset)
        with self._engine.begin() as conn:
            result = conn.execute(
                update(t).where(t.c.id == preset.id.value).values(**values)
            )
            if result.rowcount == 0:
                raise LookupError(
                    f"table maintenance preset {preset.id.value} does not exist"
                )
        return preset

    def delete(self, entity_id: EntityId) -> None:
        """Delete the preset with the given id."""
        with self._engine.begin() as conn:
            conn.execute(delete(t).where(t.c.id == entity_id.value))

    def find_by_name(self, name: str) -> TableMaintenancePreset | None:
        """Return the preset with exactly this name, or None."""
        with self._engine.connect() as conn:
            row = conn.execute(select(t).where(t.c.name == name)).first()
        return (
            None
            if row is None
            else TableMaintenancePresetRowMapper.to_aggregate(row._mapping)
        )
