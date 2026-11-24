"""Test KubernetesApi, the e2e's client for the one Deployment it may restart."""

from __future__ import annotations

import json
import ssl

import httpx
import pytest

from e2e.support import KubernetesApi

DEPLOYMENT = "/apis/apps/v1/namespaces/lakehouse-control-plane/deployments/table-maintenance-worker"


def _api(answer) -> tuple[KubernetesApi, list[tuple[str, str, str | None, object]]]:
    seen: list[tuple[str, str, str | None, object]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        seen.append((request.method, request.url.path, request.headers.get("content-type"), body))
        return answer(request)

    return KubernetesApi(httpx.Client(transport=httpx.MockTransport(handle), base_url="https://kubernetes")), seen


def test_a_restart_patches_the_pod_template_as_rollout_restart_does():
    """The restartedAt annotation of the template changes, which rolls the pods."""
    api, seen = _api(lambda request: httpx.Response(200, json={}))
    stamp = api.restart_deployment("lakehouse-control-plane", "table-maintenance-worker")
    [(method, path, content_type, body)] = seen
    assert (method, path, content_type) == ("PATCH", DEPLOYMENT, "application/strategic-merge-patch+json")
    assert body == {"spec": {"template": {"metadata": {"annotations": {"kubectl.kubernetes.io/restartedAt": stamp}}}}}
    assert stamp.endswith("Z")


def test_a_refused_call_fails_with_its_answer():
    """A 403 (the Role does not allow it) names the call and Kubernetes's message."""
    api, _ = _api(lambda request: httpx.Response(403, json={"message": "forbidden"}))
    with pytest.raises(AssertionError, match=r"GET .*table-maintenance-worker answered 403: .*forbidden"):
        api.deployment("lakehouse-control-plane", "table-maintenance-worker")


def test_the_service_account_gives_the_address_token_and_ca(tmp_path):
    """Inside a pod the client talks to the API server with the mounted token and CA."""
    (tmp_path / "token").write_text("t0ken\n")
    (tmp_path / "ca.crt").write_text("")
    environ = {"KUBERNETES_SERVICE_HOST": "10.0.0.1", "KUBERNETES_SERVICE_PORT": "443"}
    seen: dict[str, object] = {}

    def http_factory(**kwargs: object) -> httpx.Client:
        seen.update(kwargs)
        return httpx.Client()

    trusted: list[str] = []
    context = ssl.create_default_context()

    def ssl_context(cafile: str) -> ssl.SSLContext:
        trusted.append(cafile)
        return context

    KubernetesApi.from_service_account(environ, account=tmp_path, http_factory=http_factory, ssl_context=ssl_context)
    assert seen["base_url"] == "https://10.0.0.1:443"
    assert seen["headers"] == {"Authorization": "Bearer t0ken"}
    assert (seen["verify"], trusted) == (context, [str(tmp_path / "ca.crt")])
