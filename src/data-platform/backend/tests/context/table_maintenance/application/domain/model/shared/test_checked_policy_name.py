"""Test the checked_policy_name rule shared by the policy name value objects."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.shared import checked_policy_name


@pytest.mark.parametrize("name", ["gold", "a", "x" * 64, "nightly_v2", "mp-nightly", "MP-00000000000000000000000000"])
def test_checked_policy_name_accepts_a_name(name: str):
    """A name of 1 to 64 letters, digits, ``_`` or ``-`` that is not shaped like an id is returned unchanged."""
    assert checked_policy_name(name) == name


def test_checked_policy_name_refuses_an_id_shaped_name():
    """A name shaped like a prefixed id of any prefix is refused."""
    with pytest.raises(ValueError, match="must not look like a prefixed id"):
        checked_policy_name("dp-01h2xcejqtf2nbrexx3vqjhp41")


def test_checked_policy_name_refuses_a_space():
    """A space is not one of the allowed characters."""
    with pytest.raises(ValueError, match="1 to 64 letters, digits, underscores or hyphens"):
        checked_policy_name("a b")


@pytest.mark.parametrize("name", ["", "x" * 65, "a/b"])
def test_checked_policy_name_refuses_a_name_off_the_pattern(name: str):
    """An empty, too long or slashed name is refused."""
    with pytest.raises(ValueError, match="1 to 64 letters"):
        checked_policy_name(name)
