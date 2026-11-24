"""Provide KubernetesApi, the e2e's client for the one Deployment its Role lets it restart."""

from __future__ import annotations

import os
import ssl
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

SERVICE_ACCOUNT = Path("/var/run/secrets/kubernetes.io/serviceaccount")
_RESTARTED_AT = "kubectl.kubernetes.io/restartedAt"


def _trust(cafile: str) -> ssl.SSLContext:
    return ssl.create_default_context(cafile=cafile)


class KubernetesApi:
    """Read and restart a Deployment through the API server, failing with the call and the answer."""

    def __init__(self, http: httpx.Client) -> None:
        """Call the API server ``http`` points at (its ``base_url``, token and CA)."""
        self._http = http

    @classmethod
    def from_service_account(
        cls,
        environ: Mapping[str, str] = os.environ,
        *,
        account: Path = SERVICE_ACCOUNT,
        http_factory: Callable[..., httpx.Client] = httpx.Client,
        ssl_context: Callable[[str], ssl.SSLContext] = _trust,
    ) -> KubernetesApi:
        """Talk to the cluster the pod runs in, as its ServiceAccount (``table-maintenance-e2e``)."""
        host, port = environ["KUBERNETES_SERVICE_HOST"], environ["KUBERNETES_SERVICE_PORT"]
        return cls(
            http_factory(
                base_url=f"https://{host}:{port}",
                headers={"Authorization": f"Bearer {(account / 'token').read_text().strip()}"},
                verify=ssl_context(str(account / "ca.crt")),
                timeout=30,
            )
        )

    def deployment(self, namespace: str, name: str) -> dict[str, Any]:
        """Read the Deployment."""
        return self._call("GET", _path(namespace, name))

    def restart_deployment(self, namespace: str, name: str) -> str:
        """Roll the Deployment's pods as ``kubectl rollout restart`` does, and return the annotation's value."""
        stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        patch = {"spec": {"template": {"metadata": {"annotations": {_RESTARTED_AT: stamp}}}}}
        self._call(
            "PATCH", _path(namespace, name), patch, headers={"Content-Type": "application/strategic-merge-patch+json"}
        )
        return stamp

    def _call(
        self, method: str, path: str, body: dict[str, Any] | None = None, headers: dict[str, str] | None = None
    ) -> dict[str, Any]:
        reply = self._http.request(method, path, json=body, headers=headers)
        assert reply.is_success, f"{method} {path} answered {reply.status_code}: {reply.text}"
        return reply.json()


def _path(namespace: str, name: str) -> str:
    return f"/apis/apps/v1/namespaces/{namespace}/deployments/{name}"
