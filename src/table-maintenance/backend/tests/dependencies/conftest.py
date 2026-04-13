from __future__ import annotations

import pytest

from dependencies.k8s import get_k8s_api
from dependencies.settings import get_settings


@pytest.fixture(autouse=True)
def _clear_caches():
    get_settings.cache_clear()
    get_k8s_api.cache_clear()
    yield
    get_settings.cache_clear()
    get_k8s_api.cache_clear()
