"""Test namespace_prefix, which turns a namespace's location into the storage prefix its cleanup removes."""

from __future__ import annotations

import pytest

from e2e.support import namespace_prefix


def test_the_location_becomes_bucket_and_key():
    """The scheme and the trailing slash go."""
    assert namespace_prefix("s3://lake/warehouse/e2e_1a2b3c4d_orders/", "e2e_1a2b3c4d_orders") == (
        "lake/warehouse/e2e_1a2b3c4d_orders"
    )


@pytest.mark.parametrize(
    "location",
    ["s3://lake/warehouse/", "s3://lake/warehouse/other/", "s3://lake/e2e_1a2b3c4d_orders_old/", "s3://lake/"],
)
def test_a_location_that_does_not_end_in_the_namespace_is_refused(location):
    """A cleanup never removes a prefix wider than the namespace's own directory."""
    with pytest.raises(AssertionError, match="is not the namespace's own directory"):
        namespace_prefix(location, "e2e_1a2b3c4d_orders")


def test_a_namespace_at_the_bucket_root_is_refused():
    """The bucket itself is never a namespace's prefix."""
    with pytest.raises(AssertionError, match="is not the namespace's own directory"):
        namespace_prefix("s3://e2e_1a2b3c4d_orders/", "e2e_1a2b3c4d_orders")
