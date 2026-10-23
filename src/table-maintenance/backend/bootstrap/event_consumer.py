"""Polaris event consumer entry point for the table-maintenance backend."""

from __future__ import annotations

import logging
import signal
import threading

from adapter.inbound.event_consumer.kafka.kafka_event_source import KafkaEventSource
from adapter.outbound.temporal.async_loop_bridge import AsyncLoopBridge
from bootstrap.configs import get_settings
from bootstrap.container import (
    build_connected_use_cases,
    configure_logging,
    run_event_consumer,
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Consume Polaris catalog events until SIGTERM or SIGINT."""
    settings = get_settings()
    configure_logging(settings.log_level)
    stop_event = threading.Event()

    def request_stop(signum: int, _frame: object) -> None:
        logger.info("received signal %d; stopping the event consumer", signum)
        stop_event.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    bridge = AsyncLoopBridge()
    try:
        use_cases = build_connected_use_cases(settings, bridge)
        source = KafkaEventSource(
            settings.kafka.bootstrap_servers, settings.kafka.topic
        )
        run_event_consumer(use_cases, source, stop_event)
    finally:
        bridge.close()
