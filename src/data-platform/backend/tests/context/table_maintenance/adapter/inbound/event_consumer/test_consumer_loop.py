"""Drive the consumer loop with a fake source and a fake use case."""

from __future__ import annotations

import json
import threading
from typing import TYPE_CHECKING

from context.table_maintenance.adapter.inbound.event_consumer import (
    EventRecord,
    run_consumer_loop,
)
from context.table_maintenance.application.exceptions import (
    NotFoundError,
    ValidationError,
)
from context.table_maintenance.application.port.inbound.table import (
    ProcessTableHintUseCase,
    ProcessTableHintUseCaseInput,
    ProcessTableHintUseCaseOutput,
)
from tests.context.table_maintenance.adapter.inbound.event_consumer.fake_event_source import (
    FakeEventSource,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class RecordingUseCase(ProcessTableHintUseCase):
    """Process table hint use case that records its calls and can fail as scripted."""

    def __init__(self, outcomes: Sequence[Exception | None] | None = None) -> None:
        """Hold the scripted outcomes and start with no recorded calls."""
        self.calls: list[ProcessTableHintUseCaseInput] = []
        self._outcomes = list(outcomes or [])

    def execute(self, request: ProcessTableHintUseCaseInput) -> ProcessTableHintUseCaseOutput:
        """Record the call and raise the next scripted error, or return a no-op output."""
        self.calls.append(request)
        outcome = self._outcomes.pop(0) if self._outcomes else None
        if outcome is not None:
            raise outcome
        return ProcessTableHintUseCaseOutput(action="noop")


def _record(offset: int, **fields: object) -> EventRecord:
    payload = {
        "event_type": "AFTER_UPDATE_TABLE",
        "catalog_name": "iceberg",
        "namespace": ["sales"],
        "table_name": f"t{offset}",
        **fields,
    }
    return EventRecord(json.dumps(payload).encode(), "polaris-catalog-events", 0, offset)


def _raw_record(offset: int, value: bytes | None) -> EventRecord:
    return EventRecord(value, "polaris-catalog-events", 0, offset)


def _run(
    source: FakeEventSource,
    use_case: ProcessTableHintUseCase,
    *,
    max_attempts: int = 3,
) -> list[float]:
    stop = threading.Event()
    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)

    source.stop_when_exhausted = stop
    run_consumer_loop(
        source,
        use_case,
        stop,
        max_attempts=max_attempts,
        backoff_seconds=0.5,
        sleep=sleep,
    )
    return sleeps


def test_each_event_calls_use_case_then_commits() -> None:
    """Each event calls the use case and is then committed, and the source is closed at the end."""
    records = [_record(1), _record(2)]
    source = FakeEventSource(list(records))
    use_case = RecordingUseCase()

    _run(source, use_case)

    assert [c.table for c in use_case.calls] == ["t1", "t2"]
    assert source.committed == records
    assert source.closed


def test_read_events_are_committed_without_calling_use_case() -> None:
    """Read events are committed without calling the use case."""
    record = _record(1, event_type="AFTER_LOAD_TABLE")
    source = FakeEventSource([record])
    use_case = RecordingUseCase()

    _run(source, use_case)

    assert use_case.calls == []
    assert source.committed == [record]


def test_malformed_event_is_skipped() -> None:
    """A malformed event is committed and skipped without calling the use case."""
    bad = [
        _raw_record(1, b"not json"),
        _raw_record(2, None),
        _record(3, catalog_name=""),
    ]
    good = _record(4)
    source = FakeEventSource([*bad, good])
    use_case = RecordingUseCase()

    _run(source, use_case)

    assert [c.table for c in use_case.calls] == ["t4"]
    assert source.committed == [*bad, good]


def test_use_case_error_does_not_stop_loop() -> None:
    """A use case that keeps failing is given up on after its retries and the loop moves on to the next event."""
    first, second = _record(1), _record(2)
    source = FakeEventSource([first, second])
    use_case = RecordingUseCase([RuntimeError("boom")] * 3)

    _run(source, use_case)

    assert [c.table for c in use_case.calls] == ["t1", "t1", "t1", "t2"]
    assert source.committed == [first, second]


def test_transient_use_case_error_is_retried_then_committed_once() -> None:
    """A transient use case error is retried after a pause and the event is committed once."""
    record = _record(1)
    source = FakeEventSource([record])
    use_case = RecordingUseCase([RuntimeError("blip"), None])

    sleeps = _run(source, use_case)

    assert len(use_case.calls) == 2
    assert source.committed == [record]
    assert sleeps == [0.5]


def test_retry_backoff_grows_between_attempts() -> None:
    """The pause between retries grows with each attempt."""
    source = FakeEventSource([_record(1)])
    use_case = RecordingUseCase([RuntimeError("x")] * 3)

    sleeps = _run(source, use_case)

    assert sleeps == [0.5, 1.0]


def test_validation_and_not_found_errors_are_not_retried() -> None:
    """Validation and not found errors are not retried and their events are committed."""
    first, second = _record(1), _record(2)
    source = FakeEventSource([first, second])
    use_case = RecordingUseCase([ValidationError("bad"), NotFoundError("gone")])

    sleeps = _run(source, use_case)

    assert len(use_case.calls) == 2
    assert source.committed == [first, second]
    assert sleeps == []


def test_poll_exception_does_not_crash_loop() -> None:
    """An exception from poll is survived after a pause and the loop continues."""
    record = _record(1)
    source = FakeEventSource([RuntimeError("broker down"), record])
    use_case = RecordingUseCase()

    sleeps = _run(source, use_case)

    assert [c.table for c in use_case.calls] == ["t1"]
    assert source.committed == [record]
    assert sleeps == [0.5]


def test_stop_event_ends_loop_and_closes_source() -> None:
    """A set stop event ends the loop before any event and closes the source."""
    source = FakeEventSource([_record(1)])
    use_case = RecordingUseCase()
    stop = threading.Event()
    stop.set()

    run_consumer_loop(source, use_case, stop, sleep=lambda _s: None)

    assert use_case.calls == []
    assert source.closed
