"""Test BackgroundWriter, the thread that keeps writing into a partition while a scenario watches."""

from __future__ import annotations

import pytest

from e2e.support import BackgroundWriter, wait_until


def test_it_appends_until_stopped_and_says_how_many():
    """Each tick appends once, numbered from zero; stop ends the thread and returns the count."""
    made: list[int] = []
    writer = BackgroundWriter.start(made.append, every_seconds=0.01)
    wait_until(lambda: len(made) >= 3 or None, timeout=5, interval=0.01, what="three appends")
    count = writer.stop()
    assert count == len(made) >= 3
    assert made == list(range(count))
    assert not writer.running


def test_an_append_that_fails_fails_the_stop():
    """A commit conflict in the thread is raised when the scenario stops it, never lost."""

    def append(index: int) -> None:
        if index == 1:
            raise RuntimeError("CommitFailedException: conflict")

    writer = BackgroundWriter.start(append, every_seconds=0.01)
    wait_until(lambda: not writer.running or None, timeout=5, interval=0.01, what="the writer to stop on the error")
    with pytest.raises(RuntimeError, match="conflict"):
        writer.stop()


def test_stopping_twice_is_fine():
    """The scenario stops it itself and its undo stops it again."""
    writer = BackgroundWriter.start(lambda index: None, every_seconds=0.01)
    first = writer.stop()
    assert writer.stop() == first
