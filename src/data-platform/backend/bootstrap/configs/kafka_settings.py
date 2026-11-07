"""Define the KafkaSettings configuration model."""

from __future__ import annotations

from pydantic import BaseModel


class KafkaSettings(BaseModel):
    """Kafka brokers and the Polaris catalog events topic."""

    bootstrap_servers: str = "kafka-cluster-kafka-bootstrap.kafka.svc.cluster.local:9092"
    topic: str = "polaris-catalog-events"
