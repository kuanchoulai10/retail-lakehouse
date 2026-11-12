"""Provide the build_k8s_core_api function."""

from __future__ import annotations

from kubernetes import client

from bootstrap.container.load_k8s_config import load_k8s_config


def build_k8s_core_api() -> client.CoreV1Api:
    """Return the core API (pods), in-cluster or else from the kubeconfig."""
    load_k8s_config()
    return client.CoreV1Api()
