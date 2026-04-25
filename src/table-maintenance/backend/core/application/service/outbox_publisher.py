"""Define the OutboxPublisherService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.application.service.outbox_publish_result import OutboxPublishResult

if TYPE_CHECKING:
    from core.application.event_handler.event_serializer import EventSerializer
    from core.application.port.outbound.event_outbox_repo import EventOutboxRepo
    from core.base.event_dispatcher import EventDispatcher


class OutboxPublisherService:
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

    def execute(self) -> OutboxPublishResult:
        """One tick: fetch unpublished → deserialize → dispatch → mark published."""
        entries = self._outbox_repo.fetch_unpublished(batch_size=100)
        if not entries:
            return OutboxPublishResult(published_count=0)

        for entry in entries:
            event = self._serializer.deserialize(entry.event_type, entry.payload)
            self._dispatcher.dispatch(event)

        self._outbox_repo.mark_published([e.id for e in entries])
        return OutboxPublishResult(published_count=len(entries))
