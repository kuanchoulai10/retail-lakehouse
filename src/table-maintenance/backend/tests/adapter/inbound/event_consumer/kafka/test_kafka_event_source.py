"""Check KafkaEventSource against a mocked confluent-kafka consumer."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from confluent_kafka import KafkaException, TopicPartition

from adapter.inbound.event_consumer import EventRecord
from adapter.inbound.event_consumer.kafka import KafkaEventSource


def _message(*, error: object = None) -> MagicMock:
    message = MagicMock()
    message.error.return_value = error
    message.value.return_value = b"{}"
    message.topic.return_value = "polaris-catalog-events"
    message.partition.return_value = 2
    message.offset.return_value = 41
    return message


def _source() -> tuple[KafkaEventSource, MagicMock, MagicMock]:
    consumer = MagicMock()
    factory = MagicMock(return_value=consumer)
    source = KafkaEventSource(
        "broker:9092", "polaris-catalog-events", consumer_factory=factory
    )
    return source, consumer, factory


def test_configures_group_offsets_and_subscribes() -> None:
    _, consumer, factory = _source()

    factory.assert_called_once_with(
        {
            "bootstrap.servers": "broker:9092",
            "group.id": "table-maintenance-event-consumer",
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,
        }
    )
    consumer.subscribe.assert_called_once_with(["polaris-catalog-events"])


def test_poll_returns_record() -> None:
    source, consumer, _ = _source()
    consumer.poll.return_value = _message()

    assert source.poll(1.0) == EventRecord(b"{}", "polaris-catalog-events", 2, 41)
    consumer.poll.assert_called_once_with(1.0)


def test_poll_returns_none_without_message() -> None:
    source, consumer, _ = _source()
    consumer.poll.return_value = None

    assert source.poll(1.0) is None


def test_poll_raises_on_broker_error() -> None:
    source, consumer, _ = _source()
    consumer.poll.return_value = _message(error=MagicMock())

    with pytest.raises(KafkaException):
        source.poll(1.0)


def test_commit_stores_next_offset_synchronously() -> None:
    source, consumer, _ = _source()

    source.commit(EventRecord(b"{}", "polaris-catalog-events", 2, 41))

    consumer.commit.assert_called_once()
    kwargs = consumer.commit.call_args.kwargs
    assert kwargs["asynchronous"] is False
    [tp] = kwargs["offsets"]
    assert (tp.topic, tp.partition, tp.offset) == ("polaris-catalog-events", 2, 42)
    assert isinstance(tp, TopicPartition)


def test_close_closes_consumer() -> None:
    source, consumer, _ = _source()

    source.close()

    consumer.close.assert_called_once_with()
