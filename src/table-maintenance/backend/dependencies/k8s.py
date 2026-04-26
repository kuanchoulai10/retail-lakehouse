"""Provide the Kubernetes API client dependency."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from kubernetes import config as k8s_config
from kubernetes.config.config_exception import ConfigException

if TYPE_CHECKING:
    from kubernetes.client import CustomObjectsApi


@lru_cache
def get_k8s_api() -> CustomObjectsApi:
    """Return a cached Kubernetes CustomObjectsApi client."""
    from kubernetes.client import CustomObjectsApi

    try:
        k8s_config.load_incluster_config()
    except ConfigException:
        k8s_config.load_kube_config()
    return CustomObjectsApi()
