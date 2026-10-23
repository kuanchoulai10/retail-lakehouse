"""API entry point for the table-maintenance backend."""

from __future__ import annotations

import uvicorn

from adapter.inbound.web.create_app import create_app
from adapter.outbound.temporal.async_loop_bridge import AsyncLoopBridge
from bootstrap.configs import get_settings
from bootstrap.container import (
    build_connected_use_cases,
    build_web_use_cases,
    configure_logging,
)

HOST = "0.0.0.0"  # noqa: S104
PORT = 8000


def main() -> None:
    """Serve the control plane API on port 8000 until uvicorn is stopped."""
    settings = get_settings()
    configure_logging(settings.log_level)
    bridge = AsyncLoopBridge()
    try:
        use_cases = build_connected_use_cases(settings, bridge)
        app = create_app(build_web_use_cases(use_cases))
        uvicorn.run(app, host=HOST, port=PORT, log_level=settings.log_level.lower())
    finally:
        bridge.close()
