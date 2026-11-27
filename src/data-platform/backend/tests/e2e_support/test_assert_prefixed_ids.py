"""Test assert_prefixed_ids, which checks that the API's ids carry the prefix of their kind (ADR 0011)."""

from __future__ import annotations

import pytest

from e2e.support import assert_prefixed_ids

ID = "01m85cfr46e2psvhsgrbwtw7kv"


def test_ids_with_their_kinds_prefix_pass():
    """``<prefix>-<26 base32 characters>`` is the shape of every id."""
    assert_prefixed_ids({"mr": [f"mr-{ID}"], "dp": [f"dp-{ID}", f"dp-{ID}"]})


@pytest.mark.parametrize("value", [f"rc-{ID}", ID, f"mr-{ID[:-1]}", f"mr-{ID.upper()}"])
def test_an_id_of_another_shape_fails(value):
    """Another kind's prefix, no prefix, a short or an upper-case id are refused."""
    with pytest.raises(AssertionError, match="is not mr-<26 base32 characters>"):
        assert_prefixed_ids({"mr": [value]})


def test_a_kind_with_no_ids_fails():
    """An empty list proves nothing."""
    with pytest.raises(AssertionError, match="no dp id to check"):
        assert_prefixed_ids({"dp": []})
