"""Provide the run_migrations function."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from bootstrap.container.build_repositories import build_repositories
from bootstrap.container.seed_default_preset import seed_default_preset
from context.table_maintenance.adapter.outbound.shared.sql import create_schema
from context.table_maintenance.application.service.table_maintenance_preset import (
    CreateTableMaintenancePresetService,
    ListTableMaintenancePresetsService,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine

logger = logging.getLogger(__name__)


def run_migrations(engine: Engine) -> None:
    """Create the missing tables, then seed the default preset once.

    ``create_schema`` adds missing tables and applies its idempotent column
    upgrades. No discovery rule is seeded.
    """
    create_schema(engine)
    presets = build_repositories(engine).table_maintenance_presets
    created = seed_default_preset(
        ListTableMaintenancePresetsService(presets),
        CreateTableMaintenancePresetService(presets),
    )
    logger.info("schema ready; default preset %s", "created" if created else "kept")
