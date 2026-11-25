"""Provide the run_event_consumer function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.adapter.inbound.event_consumer import run_consumer_loop

if TYPE_CHECKING:
    import threading

    from context.table_maintenance.adapter.inbound.event_consumer import EventSource
    from context.table_maintenance.application.port.inbound.table import ProcessTableHintUseCase


def run_event_consumer(
    process_table_hint: ProcessTableHintUseCase, source: EventSource, stop_event: threading.Event
) -> None:
    """Feed the Polaris events to the table hint use case until stopped."""
    run_consumer_loop(source, process_table_hint, stop_event)
