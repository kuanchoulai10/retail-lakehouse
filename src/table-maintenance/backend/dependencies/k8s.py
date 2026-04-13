from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from shared.k8s.client import load_k8s_config

if TYPE_CHECKING:
    from kubernetes.client import CustomObjectsApi


@lru_cache
def get_k8s_api() -> CustomObjectsApi:
    from kubernetes.client import CustomObjectsApi

    load_k8s_config()
    return CustomObjectsApi()
