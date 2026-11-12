"""Define the run_maintenance function."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from error_text import error_text
from result_callback import post_result
from sql_builder import build_call_statements

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from job_request import JobRequest

logger = logging.getLogger(__name__)

PEAK_HEAP_PERCENT = "peak_heap_percent"

REWRITE_DATA_FILES = "rewrite_data_files"


def _sum_integers(rows: list[Any]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for row in rows:
        for name, value in row.asDict().items():
            if isinstance(value, int) and not isinstance(value, bool):
                totals[name] = totals.get(name, 0) + value
    return totals


def _check_rewrite_progress(statement: str, totals: dict[str, int]) -> None:
    """Fail a partial-progress CALL that committed nothing; log a partial failure."""
    failed = totals.get("failed_data_files_count", 0)
    if failed <= 0:
        return
    rewritten = totals.get("rewritten_data_files_count", 0)
    if rewritten == 0:
        raise RuntimeError(
            f"rewrite_data_files reported {failed} failed data files and none rewritten; no file group was committed"
        )
    logger.warning(
        "rewrite_data_files partially failed: %d rewritten, %d failed (%s)",
        rewritten,
        failed,
        statement,
    )


def _add_peak(metrics: dict[str, int], measure: Callable[[], int | None]) -> None:
    try:
        peak = measure()
    except Exception:
        logger.exception("Measuring the peak heap use failed")
        return
    if peak is not None:
        metrics[PEAK_HEAP_PERCENT] = peak


def run_maintenance(
    request: JobRequest,
    sql: Callable[[str], Any],
    *,
    measure: Callable[[], int | None] | None = None,
    stop: Callable[[], None] | None = None,
    post: Callable[[str, dict[str, Any]], bool] = post_result,
) -> int:
    """Run every planned CALL, stop the session, post the result and return the exit code.

    ``stop`` runs before the callback because the control plane deletes the
    SparkApplication once the callback of its last operation arrives; stopping first
    lets Spark finish its event log before the driver can be killed. ``measure``
    runs on success, before ``stop`` while the session can still be read, and its
    peak heap percent joins the metrics when it has one.
    """
    metrics: dict[str, int] = {}
    error: str | None = None
    try:
        for statement in build_call_statements(request):
            logger.info("SQL: %s", statement)
            totals = _sum_integers(sql(statement).collect())
            if request.operation == REWRITE_DATA_FILES:
                _check_rewrite_progress(statement, totals)
            for name, value in totals.items():
                metrics[name] = metrics.get(name, 0) + value
    except Exception as exc:
        logger.exception("Maintenance failed")
        error = error_text(exc)
    succeeded = error is None
    if succeeded and measure is not None:
        _add_peak(metrics, measure)
    body = {
        "run_id": request.run_id,
        "operation": request.operation,
        "attempt": request.attempt,
        "succeeded": succeeded,
        "metrics": metrics if succeeded else {},
        "error": error,
    }
    if stop is not None:
        try:
            stop()
        except Exception:
            logger.exception("Stopping the Spark session failed")
    try:
        delivered = post(request.callback_url, body)
    except Exception:
        logger.exception("Result callback raised")
        delivered = False
    if not delivered:
        logger.error("Result callback was not delivered; the workflow will poll")
    return 0 if succeeded else 1
