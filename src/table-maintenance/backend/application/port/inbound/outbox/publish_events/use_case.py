"""Define the PublishEventsUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase

from application.port.inbound.outbox.publish_events.output import (
    PublishEventsUseCaseOutput,
)


class PublishEventsUseCase(UseCase[None, PublishEventsUseCaseOutput]):
    """Fetch unpublished outbox entries, dispatch events, mark as published."""
