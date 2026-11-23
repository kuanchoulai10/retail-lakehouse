"""Test the SpecPartitions value object."""

from __future__ import annotations

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.shared import (
    PartitionFieldInfo,
    PartitionSpecInfo,
    SpecPartitions,
)

REGION = PartitionSpecInfo(
    spec_id=0,
    fields=(
        PartitionFieldInfo(field_id=1000, name="r", source_column="region", source_type="string", transform="identity"),
    ),
)


def test_holds_the_values_of_one_spec():
    """The partitions of one spec are its values, one tuple per partition."""
    selection = SpecPartitions(spec=REGION, values=(("eu",), (None,)))
    assert selection.values == (("eu",), (None,))


def test_round_trips_through_primitives():
    """The selection is stored and sent as JSON and read back equal."""
    selection = SpecPartitions(spec=REGION, values=(("eu",),))
    assert SpecPartitions.from_primitives(selection.to_primitives()) == selection


def test_needs_a_partition():
    """An empty selection would scope nothing, which is the whole table, written another way."""
    with pytest.raises(InvariantViolation, match="at least one partition"):
        SpecPartitions(spec=REGION, values=())


def test_each_partition_has_one_value_per_field():
    """A partition whose values do not match the spec's fields cannot be read."""
    with pytest.raises(InvariantViolation, match="has 2 values but spec 0 has 1 fields"):
        SpecPartitions(spec=REGION, values=(("eu", "x"),))


def test_an_unpartitioned_spec_has_no_selection():
    """A spec with nothing to filter on cannot scope a compaction."""
    spec = PartitionSpecInfo(spec_id=1, fields=())
    with pytest.raises(InvariantViolation, match="unpartitioned"):
        SpecPartitions(spec=spec, values=((),))
