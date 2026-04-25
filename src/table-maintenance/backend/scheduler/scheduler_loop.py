"""Define the scheduler polling loop."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.application.service.schedule_jobs import ScheduleJobsService

logger = logging.getLogger(__name__)


class SchedulerLoop:
    """Poll the database and trigger due jobs on a fixed interval."""

    def __init__(
        self, service: ScheduleJobsService, interval_seconds: int = 30
    ) -> None:
        """Initialize with a scheduling service and polling interval."""
        self._service = service
        self._interval = interval_seconds
        self._stop = threading.Event()

    def tick(self) -> None:
        """Run one scheduling iteration."""
        try:
            result = self._service.execute()
            logger.info("Scheduler tick: triggered %d job(s)", result.triggered_count)
        except Exception:
            logger.exception("Scheduler tick failed")

    def start(self) -> None:
        """Start the polling loop until stop() is called."""
        logger.info("Scheduler started (interval=%ds)", self._interval)
        while not self._stop.is_set():
            self.tick()
            self._stop.wait(self._interval)
        logger.info("Scheduler stopped")

    def stop(self) -> None:
        """Signal the loop to stop."""
        self._stop.set()
