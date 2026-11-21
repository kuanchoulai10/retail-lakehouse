"""Test the content_with_minted_rule_ids function."""

from __future__ import annotations

import itertools

import pytest

from context.table_maintenance.application.service.table_discovery_policy import content_with_minted_rule_ids

KEPT = "dr-00000000000000000000000009"


def _ids():
    counter = itertools.count(1)
    return lambda: f"dr-{next(counter):026d}"


def test_mints_an_id_for_each_rule_without_one_and_keeps_the_others():
    """An absent or null id gets the next id; a sent id is kept; only the issued ids are returned."""
    content = {
        "no_match_outcome": "unmanage",
        "rules": [{"outcome": "manage"}, {"id": KEPT, "outcome": "manage"}, {"id": None, "outcome": "unmanage"}],
    }

    minted, new_ids = content_with_minted_rule_ids(content, _ids())

    assert [rule["id"] for rule in minted["rules"]] == [
        "dr-00000000000000000000000001",
        KEPT,
        "dr-00000000000000000000000002",
    ]
    assert new_ids == frozenset({"dr-00000000000000000000000001", "dr-00000000000000000000000002"})
    assert minted["no_match_outcome"] == "unmanage"
    assert "id" not in content["rules"][0]


def test_an_empty_rule_id_is_refused():
    """``"id": ""`` is neither a ``dr-`` id nor absent."""
    with pytest.raises(ValueError, match="a rule id is a dr- id or absent"):
        content_with_minted_rule_ids({"rules": [{"id": ""}]}, _ids())


def test_content_without_rules_is_returned_unchanged():
    """No rules, nothing minted."""
    assert content_with_minted_rule_ids({"no_match_outcome": "manage"}, _ids()) == (
        {"no_match_outcome": "manage"},
        frozenset(),
    )
