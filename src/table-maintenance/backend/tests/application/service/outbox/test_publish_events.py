"""Tests for PublishEventsService."""

from __future__ import annotations

from unittest.mock import MagicMock

from application.port.inbound.outbox.publish_events import (
    PublishEventsUseCase,
)
from application.service.outbox.publish_events import PublishEventsService


def _make_service():
    """Provide a PublishEventsService with mocked collaborators."""
    outbox_repo = MagicMock()
    serializer = MagicMock()
    dispatcher = MagicMock()
    service = PublishEventsService(outbox_repo, serializer, dispatcher)
    return service, outbox_repo, serializer, dispatcher


def test_service_implements_use_case():
    """Verify that PublishEventsService implements PublishEventsUseCase."""
    service, *_ = _make_service()
    assert isinstance(service, PublishEventsUseCase)


def test_no_unpublished_returns_zero():
    """Verify that execute returns zero when no entries are unpublished."""
    service, outbox_repo, _, _ = _make_service()
    outbox_repo.fetch_unpublished.return_value = []
    result = service.execute(None)
    assert result.published_count == 0


def test_dispatches_and_marks_published():
    """Verify that execute deserializes, dispatches, and marks entries published."""
    service, outbox_repo, serializer, dispatcher = _make_service()
    entry = MagicMock()
    entry.id = "e1"
    entry.event_type = "JobTriggered"
    entry.payload = '{"job_id": "j1"}'
    outbox_repo.fetch_unpublished.return_value = [entry]
    fake_event = MagicMock()
    serializer.deserialize.return_value = fake_event

    result = service.execute(None)

    assert result.published_count == 1
    serializer.deserialize.assert_called_once_with("JobTriggered", '{"job_id": "j1"}')
    dispatcher.dispatch.assert_called_once_with(fake_event)
    outbox_repo.mark_published.assert_called_once_with(["e1"])
