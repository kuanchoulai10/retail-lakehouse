"""Tests for SchedulerSettings."""

from __future__ import annotations

from bootstrap.configs.scheduler_settings import SchedulerSettings


def test_default_interval():
    """Verify default interval is 30 seconds."""
    settings = SchedulerSettings()
    assert settings.interval_seconds == 30


def test_custom_interval():
    """Verify interval can be overridden."""
    settings = SchedulerSettings(interval_seconds=60)
    assert settings.interval_seconds == 60
