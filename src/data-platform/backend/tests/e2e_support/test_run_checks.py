"""Test the checks the full scenarios make on the maintenance runs the API returns."""

from __future__ import annotations

import pytest

from e2e.support import assert_attempts_timed, assert_runs_succeeded


def _attempt(**changes):
    return {
        "status": "succeeded",
        "size": "S",
        "started_at": "2026-11-24T01:00:00Z",
        "started_running_at": "2026-11-24T01:00:05.5Z",
        "finished_at": "2026-11-24T01:01:00+00:00",
        "event_log_finished": True,
    } | changes


def _run(operation="rewrite_data_files", status="succeeded", metrics=None, attempts=None):
    return {
        "run_id": "mr-1",
        "operation": operation,
        "status": status,
        "error": None,
        "metrics": {"rewritten_data_files_count": 4} if metrics is None else metrics,
        "attempts": [_attempt()] if attempts is None else attempts,
    }


def test_succeeded_runs_with_sized_attempts_and_finished_event_logs_pass():
    """A compaction that rewrote files, and any other operation, pass."""
    assert_runs_succeeded([_run(), _run(operation="expire_snapshots", metrics={})])


@pytest.mark.parametrize(
    ("run", "message"),
    [
        (_run(status="failed"), "did not succeed"),
        (_run(attempts=[]), "lack a size or a finished event log"),
        (_run(attempts=[_attempt(size=None)]), "lack a size or a finished event log"),
        (_run(attempts=[_attempt(event_log_finished=None)]), "lack a size or a finished event log"),
        (_run(metrics={"rewritten_data_files_count": 0}), "rewritten_data_files_count is 0"),
    ],
)
def test_a_run_that_did_not_do_its_work_fails(run, message):
    """A failed run, a missing attempt, size or event log, or a compaction that rewrote nothing fails."""
    with pytest.raises(AssertionError, match=message):
        assert_runs_succeeded([run])


def test_a_lost_callback_excuses_the_event_log_and_the_rewritten_count():
    """When the run completed without its callback, the numbers it would have sent are not required."""
    lost = {"completed_without_callback": 1}
    assert_runs_succeeded([_run(metrics=lost, attempts=[_attempt(event_log_finished=None)])])


def test_attempts_that_ran_between_their_submit_and_their_end_pass():
    """Timestamps with a fraction, a Z or an offset compare as times."""
    assert_attempts_timed([_run(attempts=[_attempt(), _attempt(status="failed", started_running_at=None)])])


@pytest.mark.parametrize(
    "attempts",
    [
        [],
        [_attempt(status="failed")],
        [_attempt(started_running_at=None)],
        [_attempt(finished_at=None)],
        [_attempt(started_running_at="2026-11-24T00:59:59Z")],
        [_attempt(finished_at="2026-11-24T01:00:04Z")],
    ],
)
def test_attempts_out_of_order_or_none_succeeded_fail(attempts):
    """No succeeded attempt, a missing time, or a start outside submit and end fails."""
    with pytest.raises(AssertionError, match="lacks started_running_at between started_at and finished_at"):
        assert_attempts_timed([_run(attempts=attempts)])
