"""Database migration entry point for the table-maintenance backend."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bootstrap.container import build_engine, configure_logging, run_migrations, wait_for_schema

if TYPE_CHECKING:
    from bootstrap.configs import MigrateSettings


def main(settings: MigrateSettings, *, wait: bool = False) -> None:
    """Create the schema and seed the default policies, then exit.

    With ``wait`` it creates nothing: it returns once another run of the migrations has done so,
    which is how the services wait for the schema before they start.
    """
    configure_logging(settings.log_level)
    engine = build_engine(settings.database)
    try:
        if wait:
            wait_for_schema(engine)
        else:
            run_migrations(engine)
    finally:
        engine.dispose()
