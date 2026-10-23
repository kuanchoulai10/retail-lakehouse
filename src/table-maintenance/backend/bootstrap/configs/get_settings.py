"""Provide the get_settings function."""

from __future__ import annotations

from functools import lru_cache

from bootstrap.configs.app_settings import AppSettings


@lru_cache
def get_settings() -> AppSettings:
    """Return the process-wide AppSettings, read from the environment once."""
    return AppSettings()
