"""Tests for the PartitionKey value object."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from context.table_maintenance.application.domain.model.compaction_candidate import PartitionKey


def test_canonical_differs_for_the_same_values_under_two_spec_ids():
    """Two specs with the same values are two partitions."""
    assert PartitionKey(spec_id=0, values=("eu",)).canonical() != PartitionKey(spec_id=1, values=("eu",)).canonical()


def test_canonical_is_stable_json_of_spec_and_values():
    """The canonical form is the JSON of the spec id and the values, so it is the same on every read."""
    key = PartitionKey(spec_id=2, values=(19000, "o'neil", None, 1.5, True))
    assert key.canonical() == '[2,[19000,"o\'neil",null,1.5,true]]'


def test_canonical_tells_an_int_from_a_string():
    """A value 1 and a value "1" are different partitions."""
    assert PartitionKey(spec_id=0, values=(1,)).canonical() != PartitionKey(spec_id=0, values=("1",)).canonical()


def test_whole_table_has_no_spec_and_no_values():
    """The whole-table key stands for the whole table."""
    whole = PartitionKey.whole_table()
    assert whole.spec_id == -1
    assert whole.values == ()
    assert whole.is_whole_table
    assert not PartitionKey(spec_id=0, values=()).is_whole_table


def test_whole_table_spec_takes_no_values():
    """A whole-table key with values cannot exist."""
    with pytest.raises(ValidationError):
        PartitionKey(spec_id=-1, values=("eu",))


def test_from_canonical_round_trips():
    """A key read back from its canonical form is the same key."""
    key = PartitionKey(spec_id=3, values=(7, "x", None))
    assert PartitionKey.from_canonical(key.canonical()) == key
