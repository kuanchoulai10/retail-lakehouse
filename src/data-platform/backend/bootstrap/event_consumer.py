"""Polaris event consumer entry point for the table-maintenance backend."""

from __future__ import annotations

import logging
import signal
import threading
from typing import TYPE_CHECKING

from adapter.inbound.event_consumer.kafka import KafkaEventSource
from adapter.hybrid.temporal.outbound.shared import AsyncLoopBridge
from bootstrap.configs import get_settings
from bootstrap.container import (
    build_connected_use_cases,
    configure_logging,
    run_event_consumer,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from adapter.inbound.event_consumer import EventSource
    from bootstrap.configs import AppSettings
    from bootstrap.container import UseCases

logger = logging.getLogger(__name__)


def install_signal_stop(callback: Callable[[], None]) -> None:
    """Call ``callback`` on SIGTERM or SIGINT."""

    def handle(signum: int, _frame: object) -> None:
        logger.info("received signal %d; stopping the event consumer", signum)
        callback()

    signal.signal(signal.SIGTERM, handle)
    signal.signal(signal.SIGINT, handle)


def run_event_consumer_process(  # noqa: PLR0913
    settings: AppSettings,
    *,
    stop_event: threading.Event,
    bridge_factory: Callable[[], AsyncLoopBridge] = AsyncLoopBridge,
    use_cases_builder: Callable[..., UseCases] = build_connected_use_cases,
    source_factory: Callable[[str, str], EventSource] = KafkaEventSource,
    install_stop: Callable[[Callable[[], None]], None] = install_signal_stop,
) -> None:
    """Consume Polaris catalog events until a stop request sets ``stop_event``."""
    install_stop(stop_event.set)
    bridge = bridge_factory()
    try:
        use_cases = use_cases_builder(settings, bridge)
        source = source_factory(settings.kafka.bootstrap_servers, settings.kafka.topic)
        run_event_consumer(use_cases, source, stop_event)
    finally:
        bridge.close()


def main() -> None:
    """Consume Polaris catalog events until SIGTERM or SIGINT."""
    settings = get_settings()
    configure_logging(settings.log_level)
    run_event_consumer_process(settings, stop_event=threading.Event())
