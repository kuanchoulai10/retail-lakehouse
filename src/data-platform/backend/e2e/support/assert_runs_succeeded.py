"""Provide assert_runs_succeeded, the check that maintenance runs did their work."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


def assert_runs_succeeded(runs: Sequence[Mapping[str, Any]]) -> None:
    """Fail unless every run succeeded with sized attempts, and a compaction rewrote files.

    A succeeded attempt has a finished event log, and the compactions together rewrote at least one
    data file, unless a run completed without its callback (the numbers it would have sent are lost).
    """
    failed = [
        {"run_id": run["run_id"], "operation": run["operation"], "status": run["status"], "error": run["error"]}
        for run in runs
        if run["status"] != "succeeded"
    ]
    assert not failed, f"runs did not succeed: {failed}"
    unfinished = [
        {"run_id": run["run_id"], "attempts": run["attempts"]}
        for run in runs
        if not run["attempts"]
        or any(attempt["size"] is None for attempt in run["attempts"])
        or (
            not _lost_callback(run)
            and any(a["status"] == "succeeded" and a["event_log_finished"] is not True for a in run["attempts"])
        )
    ]
    assert not unfinished, f"attempts lack a size or a finished event log: {unfinished}"
    compactions = [run for run in runs if run["operation"] == "rewrite_data_files"]
    if compactions and not any(_lost_callback(run) for run in compactions):
        rewritten = sum(run["metrics"].get("rewritten_data_files_count", 0) for run in compactions)
        assert rewritten > 0, f"rewritten_data_files_count is {rewritten}"


def _lost_callback(run: Mapping[str, Any]) -> bool:
    return bool(run["metrics"].get("completed_without_callback"))
