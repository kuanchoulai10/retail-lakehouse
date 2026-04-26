"""Provide outbox dependencies."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from core.adapter.outbound.sql.event_outbox_sql_repo import EventOutboxSqlRepo
from application.service.outbox.event_serializer import EventSerializer

from dependencies.settings import get_settings

if TYPE_CHECKING:
    from application.port.outbound.event_outbox_repo import EventOutboxRepo
    from core.configs import AppSettings


def get_event_serializer() -> EventSerializer:
    """Provide the EventSerializer."""
    return EventSerializer()


def get_outbox_repo(
    settings: AppSettings = Depends(get_settings),
) -> EventOutboxRepo:
    """Provide the EventOutboxRepo."""
    from dependencies.repos import _cached_sql_engine

    return EventOutboxSqlRepo(_cached_sql_engine(settings))
