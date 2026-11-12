"""Provide the build_k8s_api function."""

from __future__ import annotations

from kubernetes import client

from bootstrap.container.load_k8s_config import load_k8s_config


def build_k8s_api() -> client.CustomObjectsApi:
    """Return the custom objects API, in-cluster or else from the kubeconfig."""
    load_k8s_config()
    return client.CustomObjectsApi()
