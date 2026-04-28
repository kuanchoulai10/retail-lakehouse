"""Define the OperationProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject
from application.domain.model.catalog.table_properties.distribution_mode import (
    DistributionMode,
)
from application.domain.model.catalog.table_properties.isolation_level import (
    IsolationLevel,
)
from application.domain.model.catalog.table_properties.write_mode import WriteMode


@dataclass(frozen=True)
class OperationProperties(ValueObject):
    """Per-operation write properties shared by merge and update."""

    mode: WriteMode | None = None
    isolation_level: IsolationLevel | None = None
    distribution_mode: DistributionMode | None = None
