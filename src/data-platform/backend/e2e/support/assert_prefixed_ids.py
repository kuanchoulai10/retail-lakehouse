"""Provide assert_prefixed_ids, which checks that the API's ids carry the prefix of their kind (ADR 0011)."""

from __future__ import annotations

import re

PREFIXED = re.compile(r"^(?P<prefix>[a-z]{2,8})-[0-7][0-9a-hjkmnp-tv-z]{25}$")


def assert_prefixed_ids(ids: dict[str, list[str]]) -> None:
    """Every id is ``<prefix>-<26 base32 characters>`` with the prefix it is listed under, and no list is empty."""
    for prefix, values in ids.items():
        assert values, f"no {prefix} id to check"
        for value in values:
            shaped = PREFIXED.match(value)
            assert shaped and shaped["prefix"] == prefix, f"{value} is not {prefix}-<26 base32 characters>"
