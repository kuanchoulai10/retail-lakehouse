"""Database migration entry point for the table-maintenance backend."""

from __future__ import annotations

from bootstrap.configs import get_settings
from bootstrap.container import build_engine, configure_logging, run_migrations


def main() -> None:
    """Create the schema and seed the default template, then exit."""
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = build_engine(settings)
    try:
        run_migrations(engine)
    finally:
        engine.dispose()
