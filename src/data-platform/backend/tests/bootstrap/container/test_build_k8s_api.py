from __future__ import annotations

import pytest
from kubernetes import client, config

from bootstrap.container import build_k8s_api


def test_uses_in_cluster_config_when_available(monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []
    monkeypatch.setattr(config, "load_incluster_config", lambda: calls.append("incluster"))
    monkeypatch.setattr(config, "load_kube_config", lambda: calls.append("kube"))

    api = build_k8s_api()

    assert isinstance(api, client.CustomObjectsApi)
    assert calls == ["incluster"]


def test_falls_back_to_kube_config_outside_a_cluster(monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []

    def not_in_cluster() -> None:
        raise config.ConfigException("not in a cluster")

    monkeypatch.setattr(config, "load_incluster_config", not_in_cluster)
    monkeypatch.setattr(config, "load_kube_config", lambda: calls.append("kube"))

    api = build_k8s_api()

    assert isinstance(api, client.CustomObjectsApi)
    assert calls == ["kube"]
