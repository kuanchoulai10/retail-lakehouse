"""Provide the load_k8s_config function."""

from __future__ import annotations

from kubernetes import config


def load_k8s_config() -> None:
    """Load the in-cluster Kubernetes configuration, or else the kubeconfig."""
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
