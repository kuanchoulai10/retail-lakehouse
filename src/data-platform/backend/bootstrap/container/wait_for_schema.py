"""Provide the wait_for_schema function."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from bootstrap.container.schema_is_ready import schema_is_ready

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy import Engine

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 3.0


def wait_for_schema(
    engine: Engine, *, interval_seconds: float = INTERVAL_SECONDS, sleep: Callable[[float], None] = time.sleep
) -> None:
    """Return once the migrations have run on ``engine``; never create anything."""
    while not schema_is_ready(engine):
        logger.info("the schema is not ready yet; checking again in %s seconds", interval_seconds)
        sleep(interval_seconds)
    logger.info("the schema is ready")
