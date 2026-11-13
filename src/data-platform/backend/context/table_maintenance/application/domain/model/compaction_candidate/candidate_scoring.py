"""Define the CandidateScoring value object."""

from __future__ import annotations

from pydantic import NonNegativeFloat, PositiveFloat, PositiveInt, model_validator

from base import ValueObject


class CandidateScoring(ValueObject):
    """Say how a candidate's benefit and cost weigh into its score.

    The benefit is normalised as ``min(1, reducible_files / benefit_reference_files)``
    and the cost as ``min(1, gb_hours / cost_reference_gb_hours)``: fixed bounds,
    never the spread within one table, so a score means the same on every table.
    The weights are relative; the score divides by their sum, so it stays in [0, 1].
    """

    benefit_weight: NonNegativeFloat = 0.7
    cost_weight: NonNegativeFloat = 0.3
    benefit_reference_files: PositiveInt = 100
    cost_reference_gb_hours: PositiveFloat = 1.0

    @model_validator(mode="after")
    def _some_weight(self) -> CandidateScoring:
        if self.benefit_weight + self.cost_weight <= 0:
            raise ValueError("the benefit and cost weights cannot both be zero")
        return self
