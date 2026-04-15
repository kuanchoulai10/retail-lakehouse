from __future__ import annotations

from functools import lru_cache

from configs import AppSettings


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
