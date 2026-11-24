"""Provide KubernetesApi, the e2e's client for the Kubernetes objects its Roles let it read or change."""

from __future__ import annotations

import json
import os
import ssl
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from e2e.support.watch_expired import WatchExpired

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping

SERVICE_ACCOUNT = Path("/var/run/secrets/kubernetes.io/serviceaccount")
_RESTARTED_AT = "kubectl.kubernetes.io/restartedAt"
_GONE = 404
_EXPIRED = 410


def _trust(cafile: str) -> ssl.SSLContext:
    return ssl.create_default_context(cafile=cafile)


class KubernetesApi:
    """Read, list, watch, create and delete objects by their API path, failing with the call and the answer.

    A path is the object's or collection's path on the API server, for example
    ``/apis/sparkoperator.k8s.io/v1beta2/namespaces/<ns>/sparkapplications``.
    """

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

    def get(self, path: str) -> dict[str, Any] | None:
        """Read the object, or ``None`` when it is not there."""
        reply = self._http.get(path)
        if reply.status_code == _GONE:
            return None
        assert reply.is_success, f"GET {path} answered {reply.status_code}: {reply.text}"
        return reply.json()

    def list(self, path: str, *, label_selector: str | None = None) -> dict[str, Any]:
        """List the collection, only the objects matching ``label_selector`` when one is given."""
        params = {"labelSelector": label_selector} if label_selector else None
        reply = self._http.get(path, params=params)
        assert reply.is_success, f"GET {path} answered {reply.status_code}: {reply.text}"
        return reply.json()

    def create(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """Create the object in the collection and return what the API server stored."""
        return self._call("POST", path, body)

    def delete(self, path: str) -> None:
        """Delete the object; one already gone is fine."""
        reply = self._http.delete(path)
        assert reply.is_success or reply.status_code == _GONE, (
            f"DELETE {path} answered {reply.status_code}: {reply.text}"
        )

    def watch(
        self, path: str, resource_version: str, *, label_selector: str | None = None, timeout_seconds: int = 5
    ) -> Iterator[dict[str, Any]]:
        """Yield the collection's events after ``resource_version`` until the server ends the watch.

        The server ends it after ``timeout_seconds``, so a caller can stop between watches. Raise
        ``WatchExpired`` when the version is too old (410): the caller lists again.
        """
        params = {"watch": "true", "resourceVersion": resource_version, "timeoutSeconds": str(timeout_seconds)}
        if label_selector:
            params["labelSelector"] = label_selector
        with self._http.stream("GET", path, params=params, timeout=timeout_seconds + 30) as reply:
            if reply.status_code == _EXPIRED:
                raise WatchExpired(path)
            assert reply.is_success, f"watch {path} answered {reply.status_code}: {reply.read().decode()}"
            for line in reply.iter_lines():
                if not line:
                    continue
                event = json.loads(line)
                if event["type"] == "ERROR":
                    if event["object"].get("code") == _EXPIRED:
                        raise WatchExpired(path)
                    raise AssertionError(f"watch {path} ended with {event['object']}")
                yield event

    def _call(
        self, method: str, path: str, body: dict[str, Any] | None = None, headers: dict[str, str] | None = None
    ) -> dict[str, Any]:
        reply = self._http.request(method, path, json=body, headers=headers)
        assert reply.is_success, f"{method} {path} answered {reply.status_code}: {reply.text}"
        return reply.json()


def _path(namespace: str, name: str) -> str:
    return f"/apis/apps/v1/namespaces/{namespace}/deployments/{name}"
