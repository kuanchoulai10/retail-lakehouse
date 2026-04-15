from __future__ import annotations

from dependencies.settings import get_settings
from configs import AppSettings


def test_get_settings_returns_app_settings():
    result = get_settings()
    assert isinstance(result, AppSettings)


def test_get_settings_returns_same_instance():
    a = get_settings()
    b = get_settings()
    assert a is b
