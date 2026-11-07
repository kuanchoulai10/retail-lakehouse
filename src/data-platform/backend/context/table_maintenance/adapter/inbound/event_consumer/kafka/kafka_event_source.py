"""Define the Kafka-backed EventSource."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from confluent_kafka import Consumer, KafkaException, TopicPartition

from context.table_maintenance.adapter.inbound.event_consumer import (
    EventRecord,
    EventSource,
)

if TYPE_CHECKING:
    from collections.abc import Callable

CONSUMER_GROUP_ID = "table-maintenance-event-consumer"


class KafkaEventSource(EventSource):
    """Consume one topic with manual, synchronous offset commits."""

    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        *,
        consumer_factory: Callable[[dict[str, Any]], Any] = Consumer,
    ) -> None:
        """Create a consumer in the shared group with auto-commit off and subscribe it to the topic."""
        self._consumer = consumer_factory(
            {
                "bootstrap.servers": bootstrap_servers,
                "group.id": CONSUMER_GROUP_ID,
                "auto.offset.reset": "latest",
                "enable.auto.commit": False,
            }
        )
        self._consumer.subscribe([topic])

    def poll(self, timeout: float) -> EventRecord | None:
        """Return the next Kafka message as a record, raising KafkaException on a broker error."""
        message = self._consumer.poll(timeout)
        if message is None:
            return None
        error = message.error()
        if error is not None:
            raise KafkaException(error)
        return EventRecord(
            value=message.value(),
            topic=message.topic(),
            partition=message.partition(),
            offset=message.offset(),
        )

    def commit(self, record: EventRecord) -> None:
        """Commit the offset after the record synchronously, so a restart resumes past it."""
        self._consumer.commit(
            offsets=[TopicPartition(record.topic, record.partition, record.offset + 1)],
            asynchronous=False,
        )

    def close(self) -> None:
        """Close the consumer, leaving the group."""
        self._consumer.close()
