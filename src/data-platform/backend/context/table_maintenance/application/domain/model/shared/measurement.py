"""Define the Measurement value object."""

from __future__ import annotations

from pydantic import model_validator

from base.model import ValueObject
from context.table_maintenance.application.domain.model.shared.measurement_comparison import (
    MeasurementComparison,
)
from context.table_maintenance.application.domain.model.shared.measurement_unit import (
    MeasurementUnit,
)


class Measurement(ValueObject):
    """Hold one observed value and, when it is a condition, the threshold it is compared with.

    A measurement without a threshold and comparison is context only.
    """

    key: str
    observed: int
    unit: MeasurementUnit
    threshold: int | None = None
    comparison: MeasurementComparison | None = None

    @model_validator(mode="after")
    def _threshold_and_comparison_together(self) -> Measurement:
        """Reject a threshold without a comparison, or a comparison without a threshold."""
        if (self.threshold is None) != (self.comparison is None):
            raise ValueError("threshold and comparison must be given together")
        return self

    @property
    def met(self) -> bool | None:
        """Tell whether the observed value satisfies the threshold, or None for context."""
        if self.threshold is None or self.comparison is None:
            return None
        match self.comparison:
            case MeasurementComparison.AT_LEAST:
                return self.observed >= self.threshold
            case MeasurementComparison.MORE_THAN:
                return self.observed > self.threshold
            case MeasurementComparison.LESS_THAN:
                return self.observed < self.threshold
            case MeasurementComparison.AT_MOST:
                return self.observed <= self.threshold
