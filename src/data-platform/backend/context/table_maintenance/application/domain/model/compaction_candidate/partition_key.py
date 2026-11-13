"""Define the PartitionKey value object."""

from __future__ import annotations

import json

from pydantic import model_validator

from base import ValueObject

WHOLE_TABLE_SPEC_ID = -1


class PartitionKey(ValueObject):
    """Name one partition of a table by its spec id and values, in Iceberg's internal form.

    Two specs with equal values are different partitions. The whole-table key
    (spec id -1, no values) stands for a compaction of the whole table.
    """

    spec_id: int
    values: tuple[str | int | float | bool | None, ...]

    @model_validator(mode="after")
    def _whole_table_has_no_values(self) -> PartitionKey:
        if self.spec_id == WHOLE_TABLE_SPEC_ID and self.values:
            raise ValueError("the whole-table partition key takes no values")
        if self.spec_id < WHOLE_TABLE_SPEC_ID:
            raise ValueError(f"invalid partition spec id {self.spec_id}")
        return self

    @classmethod
    def whole_table(cls) -> PartitionKey:
        """Return the key that stands for the whole table."""
        return cls(spec_id=WHOLE_TABLE_SPEC_ID, values=())

    @classmethod
    def from_canonical(cls, text: str) -> PartitionKey:
        """Read a key back from its canonical form."""
        spec_id, values = json.loads(text)
        return cls(spec_id=spec_id, values=tuple(values))

    @property
    def is_whole_table(self) -> bool:
        """Return whether the key stands for the whole table."""
        return self.spec_id == WHOLE_TABLE_SPEC_ID

    def canonical(self) -> str:
        """Return the stable JSON of ``[spec_id, values]``, the key's unique form."""
        return json.dumps([self.spec_id, list(self.values)], separators=(",", ":"), ensure_ascii=False)
