from kubernetes import config as k8s_config
from kubernetes.config.config_exception import ConfigException


def load_k8s_config() -> None:
    """Load K8S config: in-cluster if available, otherwise kubeconfig."""
    try:
        k8s_config.load_incluster_config()
    except ConfigException:
        k8s_config.load_kube_config()
