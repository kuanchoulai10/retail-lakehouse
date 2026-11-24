"""Provide assert_attempts_timed, the check that each succeeded attempt ran between its submit and its end."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


def assert_attempts_timed(runs: Sequence[Mapping[str, Any]]) -> None:
    """Fail unless some attempt succeeded and each succeeded attempt started running between its submit and end."""
    done = [attempt for run in runs for attempt in run["attempts"] if attempt["status"] == "succeeded"]
    timed = bool(done) and all(
        attempt["started_running_at"] is not None
        and attempt["finished_at"] is not None
        and _at(attempt["started_at"]) <= _at(attempt["started_running_at"]) <= _at(attempt["finished_at"])
        for attempt in done
    )
    assert timed, f"a succeeded attempt lacks started_running_at between started_at and finished_at: {done}"


def _at(text: str) -> datetime:
    return datetime.fromisoformat(text)
