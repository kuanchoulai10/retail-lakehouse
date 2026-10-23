"""Define the post_result function."""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

logger = logging.getLogger(__name__)

TRIES = 3
DELAY_SECONDS = 5


def post_result(
    url: str,
    body: dict[str, Any],
    *,
    sleep: Callable[[float], None] = time.sleep,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> bool:
    """POST the result JSON, retrying up to three times; return whether it was accepted."""
    data = json.dumps(body).encode()
    for attempt in range(1, TRIES + 1):
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with opener(request, timeout=10) as response:
                if 200 <= response.status < 300:
                    return True
                logger.warning("Callback returned HTTP %s", response.status)
        except OSError as exc:
            logger.warning("Callback attempt %s failed: %s", attempt, exc)
        if attempt < TRIES:
            sleep(DELAY_SECONDS)
    logger.error("Callback to %s failed after %s tries", url, TRIES)
    return False
