"""Provide the configure_logging function."""

from __future__ import annotations

import logging


def configure_logging(level: str) -> None:
    """Send log records of ``level`` and above to stderr with a timestamped format."""
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
