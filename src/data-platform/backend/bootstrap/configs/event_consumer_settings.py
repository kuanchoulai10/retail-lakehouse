"""Define the EventConsumerSettings configuration model."""

from __future__ import annotations

from pydantic import Field

from bootstrap.configs.catalog_settings import CatalogSettings
from bootstrap.configs.database_settings import DatabaseSettings
from bootstrap.configs.kafka_settings import KafkaSettings
from bootstrap.configs.role_settings import RoleSettings
from bootstrap.configs.temporal_settings import TemporalSettings


class EventConsumerSettings(RoleSettings):
    """The settings of ``glac event-consumer``: it turns Polaris catalog events into table hints."""

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    temporal: TemporalSettings = Field(default_factory=TemporalSettings)
    catalog: CatalogSettings = Field(default_factory=CatalogSettings)
    kafka: KafkaSettings = Field(default_factory=KafkaSettings)
