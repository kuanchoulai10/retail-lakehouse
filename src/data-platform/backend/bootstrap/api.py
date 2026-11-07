"""API entry point for the table-maintenance backend."""

from __future__ import annotations

import uvicorn

from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
    AsyncLoopBridge,
)
from bootstrap.configs import get_settings
from bootstrap.container import build_api_app, configure_logging

HOST = "0.0.0.0"  # noqa: S104
PORT = 8000


def main() -> None:
    """Serve the control plane API on port 8000 until uvicorn is stopped."""
    settings = get_settings()
    configure_logging(settings.log_level)
    bridge = AsyncLoopBridge()
    try:
        app = build_api_app(settings, bridge)
        uvicorn.run(app, host=HOST, port=PORT, log_level=settings.log_level.lower())
    finally:
        bridge.close()
