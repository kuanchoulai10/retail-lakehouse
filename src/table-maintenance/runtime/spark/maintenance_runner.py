"""Define the run_maintenance function."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from result_callback import post_result
from sql_builder import build_call_statements

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from job_request import JobRequest

logger = logging.getLogger(__name__)

MAX_ERROR_LENGTH = 4096


def _sum_integers(rows: list[Any], metrics: dict[str, int]) -> None:
    for row in rows:
        for name, value in row.asDict().items():
            if isinstance(value, int) and not isinstance(value, bool):
                metrics[name] = metrics.get(name, 0) + value


def run_maintenance(
    request: JobRequest,
    sql: Callable[[str], Any],
    *,
    post: Callable[[str, dict[str, Any]], bool] = post_result,
) -> int:
    """Run every planned CALL, post the result and return the process exit code."""
    metrics: dict[str, int] = {}
    error: str | None = None
    try:
        for statement in build_call_statements(request):
            logger.info("SQL: %s", statement)
            _sum_integers(sql(statement).collect(), metrics)
    except Exception as exc:
        logger.exception("Maintenance failed")
        error = f"{type(exc).__name__}: {exc}"[:MAX_ERROR_LENGTH]
    succeeded = error is None
    body = {
        "run_id": request.run_id,
        "operation": request.operation,
        "attempt": request.attempt,
        "succeeded": succeeded,
        "metrics": metrics if succeeded else {},
        "error": error,
    }
    try:
        delivered = post(request.callback_url, body)
    except Exception:
        logger.exception("Result callback raised")
        delivered = False
    if not delivered:
        logger.error("Result callback was not delivered; the workflow will poll")
    return 0 if succeeded else 1
