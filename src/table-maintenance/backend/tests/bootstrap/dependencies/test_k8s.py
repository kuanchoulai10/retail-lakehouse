"""Tests for get_k8s_api dependency provider."""

from __future__ import annotations

from unittest.mock import patch

from bootstrap.dependencies.k8s import get_k8s_api
from kubernetes.client import CustomObjectsApi


@patch("bootstrap.dependencies.k8s.k8s_config.load_incluster_config")
def test_get_k8s_api_returns_custom_objects_api(mock_in):
    """Verify that get_k8s_api returns a CustomObjectsApi instance."""
    get_k8s_api.cache_clear()
    result = get_k8s_api()
    assert isinstance(result, CustomObjectsApi)


@patch("bootstrap.dependencies.k8s.k8s_config.load_incluster_config")
def test_get_k8s_api_returns_same_instance(mock_in):
    """Verify that get_k8s_api returns the same cached instance on repeated calls."""
    get_k8s_api.cache_clear()
    a = get_k8s_api()
    b = get_k8s_api()
    assert a is b


@patch("bootstrap.dependencies.k8s.k8s_config.load_incluster_config")
def test_loads_k8s_config_on_first_call(mock_in):
    """Verify that get_k8s_api loads in-cluster config on first invocation."""
    get_k8s_api.cache_clear()
    get_k8s_api()
    mock_in.assert_called_once()


@patch(
    "bootstrap.dependencies.k8s.k8s_config.load_incluster_config",
    side_effect=__import__("kubernetes").config.config_exception.ConfigException(
        "not in cluster"
    ),
)
@patch("bootstrap.dependencies.k8s.k8s_config.load_kube_config")
def test_falls_back_to_kubeconfig(mock_kube, mock_in):
    """Verify that get_k8s_api falls back to kubeconfig when in-cluster fails."""
    get_k8s_api.cache_clear()
    get_k8s_api()
    mock_kube.assert_called_once()
