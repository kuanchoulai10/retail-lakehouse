"""Test misfiled_scenarios, which finds the scenarios no e2e run would select."""

from __future__ import annotations

from e2e.support import misfiled_scenarios


def test_a_scenario_of_one_kind_is_filed():
    """``critical`` or ``full`` alone puts a scenario in a run."""
    assert misfiled_scenarios([("e2e/test_a.py::test_a", {"critical"}), ("e2e/test_b.py::test_b", {"full"})]) == []


def test_a_scenario_without_a_kind_or_with_both_is_named():
    """An unmarked scenario would never run; one with both kinds is ambiguous."""
    assert misfiled_scenarios(
        [
            ("e2e/test_a.py::test_a", set()),
            ("e2e/test_b.py::test_b", {"critical", "full"}),
            ("e2e/test_c.py::test_c", {"parametrize", "full"}),
        ]
    ) == ["e2e/test_a.py::test_a has no kind", "e2e/test_b.py::test_b is both critical and full"]
