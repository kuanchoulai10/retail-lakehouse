"""API entry point for the table-maintenance backend."""

from __future__ import annotations

from typing import TYPE_CHECKING

import uvicorn

from bootstrap.container import build_api_app, configure_logging
from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
    AsyncLoopBridge,
)

if TYPE_CHECKING:
    from bootstrap.configs import ApiSettings

HOST = "0.0.0.0"  # noqa: S104
PORT = 8000


def main(settings: ApiSettings) -> None:
    """Serve the control plane API on port 8000 until uvicorn is stopped."""
    configure_logging(settings.log_level)
    bridge = AsyncLoopBridge()
    try:
        app = build_api_app(settings, bridge)
        uvicorn.run(app, host=HOST, port=PORT, log_level=settings.log_level.lower())
    finally:
        bridge.close()
