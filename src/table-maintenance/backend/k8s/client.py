"""Backward-compatible re-export. Canonical location: shared.k8s.client"""

from shared.k8s.client import load_k8s_config

__all__ = ["load_k8s_config"]
