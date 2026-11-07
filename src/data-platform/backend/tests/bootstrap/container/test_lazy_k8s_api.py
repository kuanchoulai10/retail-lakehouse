"""Test the lazily created Kubernetes API client."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bootstrap.container import LazyK8sApi


def test_factory_is_not_called_until_first_use_then_once():
    """The factory is not called until first use and then only once."""
    api = MagicMock(name="api")
    calls: list[int] = []

    def factory() -> MagicMock:
        calls.append(1)
        return api

    lazy = LazyK8sApi(factory)
    assert calls == []

    lazy.get_namespaced_custom_object(group="g")
    lazy.delete_namespaced_custom_object(group="g")

    assert calls == [1]
    api.get_namespaced_custom_object.assert_called_once_with(group="g")
    api.delete_namespaced_custom_object.assert_called_once_with(group="g")


def test_a_failing_factory_only_fails_at_first_use():
    """A failing factory raises at first use instead of at construction."""

    def factory() -> MagicMock:
        raise RuntimeError("no kubeconfig")

    lazy = LazyK8sApi(factory)

    with pytest.raises(RuntimeError, match="no kubeconfig"):
        lazy.create_namespaced_custom_object()
