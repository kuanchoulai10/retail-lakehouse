"""Test that get_settings builds the application settings once and caches them."""

from __future__ import annotations

from bootstrap.configs import AppSettings, get_settings


def test_get_settings_is_cached():
    """Repeated calls return the same AppSettings instance."""
    get_settings.cache_clear()
    try:
        first = get_settings()
        assert isinstance(first, AppSettings)
        assert get_settings() is first
    finally:
        get_settings.cache_clear()
