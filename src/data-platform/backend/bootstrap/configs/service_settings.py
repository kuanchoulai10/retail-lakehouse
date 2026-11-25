"""Define the ServiceSettings configuration model."""

from __future__ import annotations

from pydantic import Field

from bootstrap.configs.catalog_settings import CatalogSettings
from bootstrap.configs.database_settings import DatabaseSettings
from bootstrap.configs.discovery_settings import DiscoverySettings
from bootstrap.configs.maintenance_settings import MaintenanceSettings
from bootstrap.configs.metrics_settings import MetricsSettings
from bootstrap.configs.role_settings import RoleSettings
from bootstrap.configs.spark_settings import SparkSettings
from bootstrap.configs.temporal_settings import TemporalSettings


class ServiceSettings(RoleSettings):
    """The settings the API and the worker share, because both build every use case."""

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    temporal: TemporalSettings = Field(default_factory=TemporalSettings)
    catalog: CatalogSettings = Field(default_factory=CatalogSettings)
    spark: SparkSettings = Field(default_factory=SparkSettings)
    maintenance: MaintenanceSettings = Field(default_factory=MaintenanceSettings)
    discovery: DiscoverySettings = Field(default_factory=DiscoverySettings)
    metrics: MetricsSettings = Field(default_factory=MetricsSettings)
