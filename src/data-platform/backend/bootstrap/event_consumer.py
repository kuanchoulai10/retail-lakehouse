"""Polaris event consumer entry point for the table-maintenance backend."""

from __future__ import annotations

import logging
import signal
import threading
from typing import TYPE_CHECKING

from bootstrap.container import (
    build_table_hint_use_case,
    configure_logging,
    run_event_consumer,
)
from context.table_maintenance.adapter.hybrid.temporal.outbound.shared import (
    AsyncLoopBridge,
)
from context.table_maintenance.adapter.inbound.event_consumer.kafka import (
    KafkaEventSource,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from bootstrap.configs import EventConsumerSettings
    from context.table_maintenance.adapter.inbound.event_consumer import EventSource
    from context.table_maintenance.application.port.inbound.table import ProcessTableHintUseCase

logger = logging.getLogger(__name__)


def install_signal_stop(callback: Callable[[], None]) -> None:
    """Call ``callback`` on SIGTERM or SIGINT."""

    def handle(signum: int, _frame: object) -> None:
        logger.info("received signal %d; stopping the event consumer", signum)
        callback()

    signal.signal(signal.SIGTERM, handle)
    signal.signal(signal.SIGINT, handle)


def run_event_consumer_process(  # noqa: PLR0913
    settings: EventConsumerSettings,
    *,
    stop_event: threading.Event,
    bridge_factory: Callable[[], AsyncLoopBridge] = AsyncLoopBridge,
    use_case_builder: Callable[..., ProcessTableHintUseCase] = build_table_hint_use_case,
    source_factory: Callable[[str, str], EventSource] = KafkaEventSource,
    install_stop: Callable[[Callable[[], None]], None] = install_signal_stop,
) -> None:
    """Consume Polaris catalog events until a stop request sets ``stop_event``."""
    install_stop(stop_event.set)
    bridge = bridge_factory()
    try:
        process_table_hint = use_case_builder(settings, bridge)
        source = source_factory(settings.kafka.bootstrap_servers, settings.kafka.topic)
        run_event_consumer(process_table_hint, source, stop_event)
    finally:
        bridge.close()


def main(settings: EventConsumerSettings) -> None:
    """Consume Polaris catalog events until SIGTERM or SIGINT."""
    configure_logging(settings.log_level)
    run_event_consumer_process(settings, stop_event=threading.Event())
