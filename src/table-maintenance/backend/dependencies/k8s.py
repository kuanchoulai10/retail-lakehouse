from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import Request
    from kubernetes.client import CustomObjectsApi


def get_k8s_api(request: Request) -> CustomObjectsApi:
    return request.app.state.k8s_api
