"""Test wait_until, the bounded poll every e2e wait uses."""

from __future__ import annotations

import pytest

from e2e.support import wait_until


class _FakeClock:
    """A clock that moves only when the poll sleeps."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def test_returns_the_first_value_that_is_not_none():
    """The poll stops at the first answer and returns it."""
    answers = iter([None, None, "found"])
    clock = _FakeClock()
    assert (
        wait_until(lambda: next(answers), timeout=10, interval=1, what="x", clock=clock, sleep=clock.sleep) == "found"
    )
    assert clock.now == 2


def test_times_out_naming_what_it_waited_for_and_the_last_value():
    """A poll that never answers fails after the timeout, saying what it waited for and what it last saw."""
    clock = _FakeClock()
    with pytest.raises(TimeoutError, match=r"the run not seen within 3s; last: None"):
        wait_until(lambda: None, timeout=3, interval=1, what="the run", clock=clock, sleep=clock.sleep)
    assert clock.now >= 3


def test_an_exception_counts_as_not_yet_and_is_reported():
    """A probe that raises is tried again, and its last error is in the timeout message."""
    clock = _FakeClock()

    def probe() -> None:
        raise ConnectionError("refused")

    with pytest.raises(TimeoutError, match=r"last: ConnectionError\('refused'\)"):
        wait_until(probe, timeout=2, interval=1, what="the API", clock=clock, sleep=clock.sleep)
