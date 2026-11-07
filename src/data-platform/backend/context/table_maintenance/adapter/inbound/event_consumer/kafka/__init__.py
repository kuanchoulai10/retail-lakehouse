"""Kafka implementation of the event source."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.event_consumer.kafka.kafka_event_source import (
    KafkaEventSource,
)

__all__ = [
    "KafkaEventSource",
]
