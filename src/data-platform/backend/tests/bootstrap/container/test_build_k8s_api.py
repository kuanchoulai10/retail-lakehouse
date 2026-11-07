"""Test how the Kubernetes API client picks its configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kubernetes import client, config

from bootstrap.container import build_k8s_api

if TYPE_CHECKING:
    import pytest


def test_uses_in_cluster_config_when_available(monkeypatch: pytest.MonkeyPatch):
    """The in-cluster configuration is used when it loads."""
    calls: list[str] = []
    monkeypatch.setattr(config, "load_incluster_config", lambda: calls.append("incluster"))
    monkeypatch.setattr(config, "load_kube_config", lambda: calls.append("kube"))

    api = build_k8s_api()

    assert isinstance(api, client.CustomObjectsApi)
    assert calls == ["incluster"]


def test_falls_back_to_kube_config_outside_a_cluster(monkeypatch: pytest.MonkeyPatch):
    """The kubeconfig is used when the in-cluster configuration is not available."""
    calls: list[str] = []

    def not_in_cluster() -> None:
        raise config.ConfigException("not in a cluster")

    monkeypatch.setattr(config, "load_incluster_config", not_in_cluster)
    monkeypatch.setattr(config, "load_kube_config", lambda: calls.append("kube"))

    api = build_k8s_api()

    assert isinstance(api, client.CustomObjectsApi)
    assert calls == ["kube"]
