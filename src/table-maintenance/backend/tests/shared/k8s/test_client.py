from unittest.mock import patch

from kubernetes.config.config_exception import ConfigException
from shared.k8s.client import load_k8s_config


def test_uses_incluster_when_available():
    with (
        patch("shared.k8s.client.k8s_config.load_incluster_config") as mock_in,
        patch("shared.k8s.client.k8s_config.load_kube_config") as mock_kube,
    ):
        load_k8s_config()
        mock_in.assert_called_once()
        mock_kube.assert_not_called()


def test_falls_back_to_kubeconfig_when_not_in_cluster():
    with (
        patch(
            "shared.k8s.client.k8s_config.load_incluster_config",
            side_effect=ConfigException("not in cluster"),
        ),
        patch("shared.k8s.client.k8s_config.load_kube_config") as mock_kube,
    ):
        load_k8s_config()
        mock_kube.assert_called_once()
