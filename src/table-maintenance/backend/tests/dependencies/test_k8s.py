from __future__ import annotations

from unittest.mock import patch

from dependencies.k8s import get_k8s_api
from kubernetes.client import CustomObjectsApi


@patch("dependencies.k8s.load_k8s_config")
def test_get_k8s_api_returns_custom_objects_api(mock_load):
    result = get_k8s_api()
    assert isinstance(result, CustomObjectsApi)


@patch("dependencies.k8s.load_k8s_config")
def test_get_k8s_api_returns_same_instance(mock_load):
    a = get_k8s_api()
    b = get_k8s_api()
    assert a is b
