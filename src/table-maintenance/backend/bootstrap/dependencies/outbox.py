"""Provide outbox dependencies."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from adapter.outbound.sql.event_outbox_sql_store import EventOutboxSqlStore
from application.service.outbox.event_serializer import EventSerializer

from bootstrap.dependencies.settings import get_settings

if TYPE_CHECKING:
    from application.port.outbound.event_outbox.event_outbox_store import (
        EventOutboxStore,
    )
    from bootstrap.configs import AppSettings


def get_event_serializer() -> EventSerializer:
    """Provide the EventSerializer."""
    return EventSerializer()


def get_outbox_repo(
    settings: AppSettings = Depends(get_settings),
) -> EventOutboxStore:
    """Provide the EventOutboxStore."""
    from bootstrap.dependencies.repos import _cached_sql_engine

    return EventOutboxSqlStore(_cached_sql_engine(settings))
