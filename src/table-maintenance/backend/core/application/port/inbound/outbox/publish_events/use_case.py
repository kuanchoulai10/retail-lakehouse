"""Define the PublishEventsUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase

from core.application.port.inbound.outbox.publish_events.output import (
    PublishEventsResult,
)


class PublishEventsUseCase(UseCase[None, PublishEventsResult]):
    """Fetch unpublished outbox entries, dispatch events, mark as published."""
