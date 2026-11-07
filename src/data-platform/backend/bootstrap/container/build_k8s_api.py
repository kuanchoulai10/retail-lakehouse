"""Provide the build_k8s_api function."""

from __future__ import annotations

from kubernetes import client, config


def build_k8s_api() -> client.CustomObjectsApi:
    """Return the custom objects API, in-cluster or else from the kubeconfig."""
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.CustomObjectsApi()
