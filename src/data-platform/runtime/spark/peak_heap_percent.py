"""Define the peak_heap_percent function."""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import TYPE_CHECKING

from memory_bytes import memory_bytes

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MEMORY = "1g"
DRIVER_ID = "driver"
FETCH_TIMEOUT_SECONDS = 5


def _fetch_json(url: str) -> Any:  # noqa: ANN401
    with urllib.request.urlopen(url, timeout=FETCH_TIMEOUT_SECONDS) as response:  # noqa: S310
        return json.load(response)


def peak_heap_percent(spark: Any, *, fetch: Callable[[str], Any] = _fetch_json) -> int | None:  # noqa: ANN401
    """Return the largest share, in whole percent, of its heap the driver or an executor used at its peak.

    Reads the application's executors from the Spark UI's REST API while the session still runs.
    Returns None when the UI is off, cannot be read, or reports no peak heap yet (executors send
    their peaks with their heartbeats, so a very short job may have none).
    """
    context = spark.sparkContext
    ui = context.uiWebUrl
    if not ui:
        return None
    conf = context.getConf()
    try:
        executors = fetch(f"{ui}/api/v1/applications/{context.applicationId}/allexecutors")
        driver_memory = memory_bytes(conf.get("spark.driver.memory", DEFAULT_MEMORY))
        executor_memory = memory_bytes(conf.get("spark.executor.memory", DEFAULT_MEMORY))
        percents = [
            _percent(entry, driver_memory if entry.get("id") == DRIVER_ID else executor_memory) for entry in executors
        ]
    except Exception:
        logger.exception("Reading the peak heap use failed")
        return None
    measured = [p for p in percents if p is not None]
    return max(measured) if measured else None


def _percent(entry: dict[str, Any], memory: int) -> int | None:
    heap = (entry.get("peakMemoryMetrics") or {}).get("JVMHeapMemory")
    if heap is None:
        return None
    return int(heap * 100 // memory)
