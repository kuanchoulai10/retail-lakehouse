"""Define the peak_heap_bytes function."""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

logger = logging.getLogger(__name__)

PEAK_DRIVER_HEAP_BYTES = "peak_driver_heap_bytes"
PEAK_EXECUTOR_HEAP_BYTES = "peak_executor_heap_bytes"
DRIVER_ID = "driver"
DEFAULT_UI_PORT = "4040"
FETCH_TIMEOUT_SECONDS = 5


def _fetch_json(url: str) -> Any:  # noqa: ANN401
    with urllib.request.urlopen(url, timeout=FETCH_TIMEOUT_SECONDS) as response:  # noqa: S310
        return json.load(response)


def peak_heap_bytes(spark: Any, *, fetch: Callable[[str], Any] = _fetch_json) -> dict[str, int]:  # noqa: ANN401
    """Return the peak JVM heap the driver and the busiest executor used, in bytes, by metric name.

    Reads the application's executors from the Spark UI's REST API while the session still runs,
    on localhost: on Kubernetes ``uiWebUrl`` names the driver's Service, which the driver itself
    may not reach. A role with no peak yet is left out (executors send their peaks with their
    heartbeats, so a very short job may have none); nothing is measured when the UI is off or
    cannot be read.
    """
    context = spark.sparkContext
    ui = context.uiWebUrl
    if not ui:
        return {}
    port = urlsplit(ui).port or context.getConf().get("spark.ui.port", DEFAULT_UI_PORT)
    try:
        executors = fetch(f"http://localhost:{port}/api/v1/applications/{context.applicationId}/allexecutors")
        peaks: dict[str, int] = {}
        for entry in executors:
            heap = (entry.get("peakMemoryMetrics") or {}).get("JVMHeapMemory")
            if heap is None:
                continue
            key = PEAK_DRIVER_HEAP_BYTES if entry.get("id") == DRIVER_ID else PEAK_EXECUTOR_HEAP_BYTES
            peaks[key] = max(peaks.get(key, 0), int(heap))
    except Exception:
        logger.exception("Reading the peak heap use failed")
        return {}
    return peaks
