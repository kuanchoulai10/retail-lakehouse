"""Tests for get_settings dependency provider."""

from __future__ import annotations

from dependencies.settings import get_settings
from bootstrap.configs import AppSettings


def test_get_settings_returns_app_settings():
    """Verify that get_settings returns an AppSettings instance."""
    result = get_settings()
    assert isinstance(result, AppSettings)


def test_get_settings_returns_same_instance():
    """Verify that get_settings returns the same cached instance on repeated calls."""
    a = get_settings()
    b = get_settings()
    assert a is b
