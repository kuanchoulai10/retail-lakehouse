"""Define the outbox publisher polling loop."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.service.outbox.publish_events import PublishEventsService

logger = logging.getLogger(__name__)


class PublisherLoop:
    """Poll the outbox table and dispatch events on a fixed interval."""

    def __init__(
        self, service: PublishEventsService, interval_seconds: int = 5
    ) -> None:
        """Initialize with a publisher service and polling interval."""
        self._service = service
        self._interval = interval_seconds
        self._stop = threading.Event()

    def tick(self) -> None:
        """Run one publishing iteration."""
        try:
            result = self._service.execute()
            if result.published_count > 0:
                logger.info(
                    "Outbox tick: published %d event(s)", result.published_count
                )
        except Exception:
            logger.exception("Outbox tick failed")

    def start(self) -> None:
        """Start the polling loop until stop() is called."""
        logger.info("Outbox publisher started (interval=%ds)", self._interval)
        while not self._stop.is_set():
            self.tick()
            self._stop.wait(self._interval)
        logger.info("Outbox publisher stopped")

    def stop(self) -> None:
        """Signal the loop to stop."""
        self._stop.set()
