"""Database migration entry point for the table-maintenance backend."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bootstrap.container import build_engine, configure_logging, run_migrations

if TYPE_CHECKING:
    from bootstrap.configs import MigrateSettings


def main(settings: MigrateSettings) -> None:
    """Create the schema and seed the default policy, then exit."""
    configure_logging(settings.log_level)
    engine = build_engine(settings.database)
    try:
        run_migrations(engine)
    finally:
        engine.dispose()
