"""Provide the run_event_consumer function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.adapter.inbound.event_consumer import run_consumer_loop

if TYPE_CHECKING:
    import threading

    from context.table_maintenance.adapter.inbound.event_consumer import EventSource
    from bootstrap.container.use_cases import UseCases


def run_event_consumer(
    use_cases: UseCases, source: EventSource, stop_event: threading.Event
) -> None:
    """Feed the Polaris events to the table hint use case until stopped."""
    run_consumer_loop(source, use_cases.process_table_hint, stop_event)
