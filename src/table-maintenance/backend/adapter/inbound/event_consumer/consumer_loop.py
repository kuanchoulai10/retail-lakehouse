"""Run the Polaris event consumer loop."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

from adapter.inbound.event_consumer.event_record import EventRecord
from adapter.inbound.event_consumer.event_source import EventSource
from adapter.inbound.event_consumer.map_polaris_event import map_polaris_event
from application.exceptions import NotFoundError, ValidationError
from application.port.inbound.table.process_table_hint import (
    ProcessTableHintUseCase,
    ProcessTableHintUseCaseInput,
)

logger = logging.getLogger(__name__)

_POLL_TIMEOUT_SECONDS = 1.0


def _execute_with_retry(
    use_case: ProcessTableHintUseCase,
    hint: ProcessTableHintUseCaseInput,
    *,
    max_attempts: int,
    backoff_seconds: float,
    sleep: Callable[[float], None],
) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            use_case.execute(hint)
        except (ValidationError, NotFoundError) as exc:
            logger.warning("Dropping table hint %s without retry: %s", hint, exc)
            return
        except Exception:
            if attempt == max_attempts:
                logger.exception(
                    "Giving up on table hint %s after %d attempts", hint, attempt
                )
                return
            logger.warning(
                "Table hint %s failed on attempt %d, retrying",
                hint,
                attempt,
                exc_info=True,
            )
            sleep(backoff_seconds * 2 ** (attempt - 1))
        else:
            return


def _handle(
    record: EventRecord,
    use_case: ProcessTableHintUseCase,
    *,
    max_attempts: int,
    backoff_seconds: float,
    sleep: Callable[[float], None],
) -> None:
    if record.value is None:
        logger.warning(
            "Skipping empty record at %s[%d]@%d",
            record.topic,
            record.partition,
            record.offset,
        )
        return
    hint = map_polaris_event(record.value)
    if hint is None:
        return
    _execute_with_retry(
        use_case,
        hint,
        max_attempts=max_attempts,
        backoff_seconds=backoff_seconds,
        sleep=sleep,
    )


def run_consumer_loop(
    source: EventSource,
    use_case: ProcessTableHintUseCase,
    stop_event: threading.Event,
    *,
    max_attempts: int = 3,
    backoff_seconds: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Feed every Polaris event to the use case until stop_event is set.

    Every record is committed after handling, including skipped, failed and
    exhausted ones, so one poison record cannot wedge the partition. Hints lost this
    way are recovered by the periodic catalog discovery.
    """
    try:
        while not stop_event.is_set():
            try:
                record = source.poll(_POLL_TIMEOUT_SECONDS)
            except Exception:
                logger.exception("Polling the event source failed")
                sleep(backoff_seconds)
                continue
            if record is None:
                continue
            try:
                _handle(
                    record,
                    use_case,
                    max_attempts=max_attempts,
                    backoff_seconds=backoff_seconds,
                    sleep=sleep,
                )
            except Exception:
                logger.exception(
                    "Unexpected failure handling record at offset %d", record.offset
                )
            try:
                source.commit(record)
            except Exception:
                logger.exception("Committing offset %d failed", record.offset)
    finally:
        source.close()
