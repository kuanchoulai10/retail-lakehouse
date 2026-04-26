"""Tests for MessagingSettings."""

from __future__ import annotations

from bootstrap.configs.messaging_settings import MessagingSettings


def test_default_interval():
    """Verify default interval is 5 seconds."""
    settings = MessagingSettings()
    assert settings.interval_seconds == 5


def test_custom_interval():
    """Verify interval can be overridden."""
    settings = MessagingSettings(interval_seconds=10)
    assert settings.interval_seconds == 10
