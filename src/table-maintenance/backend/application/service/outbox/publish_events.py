"""Define the PublishEventsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.inbound.outbox.publish_events import (
    PublishEventsResult,
    PublishEventsUseCase,
)

if TYPE_CHECKING:
    from application.service.outbox.event_serializer import EventSerializer
    from application.port.outbound.event_outbox_repo import EventOutboxRepo
    from base.event_dispatcher import EventDispatcher


class PublishEventsService(PublishEventsUseCase):
    """Fetch unpublished outbox entries, dispatch events, mark as published."""

    def __init__(
        self,
        outbox_repo: EventOutboxRepo,
        serializer: EventSerializer,
        dispatcher: EventDispatcher,
    ) -> None:
        """Initialize with outbox repo, serializer, and event dispatcher."""
        self._outbox_repo = outbox_repo
        self._serializer = serializer
        self._dispatcher = dispatcher

    def execute(self, request: None = None) -> PublishEventsResult:
        """One tick: fetch unpublished → deserialize → dispatch → mark published."""
        entries = self._outbox_repo.fetch_unpublished(batch_size=100)
        if not entries:
            return PublishEventsResult(published_count=0)

        for entry in entries:
            event = self._serializer.deserialize(entry.event_type, entry.payload)
            self._dispatcher.dispatch(event)

        self._outbox_repo.mark_published([e.id for e in entries])
        return PublishEventsResult(published_count=len(entries))
