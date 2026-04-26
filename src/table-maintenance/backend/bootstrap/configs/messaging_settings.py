"""Messaging-specific configuration."""

from __future__ import annotations

from pydantic import BaseModel


class MessagingSettings(BaseModel):
    """Settings for the messaging (outbox publisher) component."""

    interval_seconds: int = 5
