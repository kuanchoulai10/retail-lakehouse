"""Define the SpecFilter value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class SpecFilter(ValueObject):
    """Hold the rewrite_data_files where clause for one partition spec.

    An empty ``where`` means the whole table for this spec.
    """

    spec_id: int
    where: str
