"""Test CleanupStack, which undoes what a scenario created even when the scenario fails."""

from __future__ import annotations

from e2e.support import CleanupStack


def test_runs_actions_newest_first():
    """What was created last is removed first, as a table goes before its namespace."""
    done: list[str] = []
    stack = CleanupStack()
    stack.push("namespace", lambda: done.append("namespace"))
    stack.push("table", lambda: done.append("table"))
    assert stack.run() == []
    assert done == ["table", "namespace"]


def test_a_failing_action_does_not_stop_the_rest():
    """Every action runs, and each failure is reported with what it was undoing."""
    done: list[str] = []
    stack = CleanupStack()
    stack.push("namespace", lambda: done.append("namespace"))

    def fail() -> None:
        raise RuntimeError("409 not empty")

    stack.push("table", fail)
    assert stack.run() == ["table: RuntimeError('409 not empty')"]
    assert done == ["namespace"]


def test_runs_each_action_once():
    """A second run has nothing left to do."""
    done: list[str] = []
    stack = CleanupStack()
    stack.push("table", lambda: done.append("table"))
    stack.run()
    assert stack.run() == []
    assert done == ["table"]
