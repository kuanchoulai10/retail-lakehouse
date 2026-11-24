"""Test KubernetesApi, the e2e's client for the one Deployment it may restart."""

from __future__ import annotations

import json
import ssl

import httpx
import pytest

from e2e.support import KubernetesApi, WatchExpired

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


SPARK_APPS = "/apis/sparkoperator.k8s.io/v1beta2/namespaces/lakehouse-maintenance-operations/sparkapplications"


def test_a_missing_object_reads_as_none_and_deleting_it_is_fine():
    """A 404 means "not there", which a check for absence and an idempotent undo both want."""
    api, seen = _api(lambda request: httpx.Response(404, json={"reason": "NotFound"}))
    assert api.get(f"{SPARK_APPS}/tm-rdf-x-a1") is None
    api.delete(f"{SPARK_APPS}/tm-rdf-x-a1")
    assert [(method, path) for method, path, _, _ in seen] == [
        ("GET", f"{SPARK_APPS}/tm-rdf-x-a1"),
        ("DELETE", f"{SPARK_APPS}/tm-rdf-x-a1"),
    ]


def test_a_listing_selects_by_label_and_a_create_posts_the_object():
    """The label selector goes to the API server; the created object is what it answers."""

    def answer(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            assert request.url.params["labelSelector"] == "table-maintenance/run-id"
            return httpx.Response(200, json={"metadata": {"resourceVersion": "7"}, "items": []})
        return httpx.Response(201, json={"metadata": {"name": "made"}})

    api, seen = _api(answer)
    assert api.list(SPARK_APPS, label_selector="table-maintenance/run-id")["metadata"]["resourceVersion"] == "7"
    assert api.create(SPARK_APPS, {"kind": "SparkApplication"}) == {"metadata": {"name": "made"}}
    assert seen[1][:2] == ("POST", SPARK_APPS)
    assert seen[1][3] == {"kind": "SparkApplication"}


def test_a_watch_yields_each_event_until_the_server_ends_it():
    """Events arrive one JSON object per line from the resource version given; the stream ends after its timeout."""
    lines = [
        {"type": "ADDED", "object": {"metadata": {"name": "a", "resourceVersion": "8"}}},
        {"type": "DELETED", "object": {"metadata": {"name": "a", "resourceVersion": "9"}}},
    ]

    def answer(request: httpx.Request) -> httpx.Response:
        assert dict(request.url.params) == {
            "watch": "true",
            "resourceVersion": "7",
            "timeoutSeconds": "5",
            "labelSelector": "table-maintenance/run-id",
        }
        return httpx.Response(200, content="".join(json.dumps(line) + "\n" for line in lines).encode())

    api, _ = _api(answer)
    events = list(api.watch(SPARK_APPS, "7", label_selector="table-maintenance/run-id", timeout_seconds=5))
    assert [(event["type"], event["object"]["metadata"]["name"]) for event in events] == [
        ("ADDED", "a"),
        ("DELETED", "a"),
    ]


def test_a_watch_whose_version_is_too_old_raises_watch_expired():
    """A 410 ERROR event tells the caller to list again; it is never yielded as an object."""
    expired = {"type": "ERROR", "object": {"kind": "Status", "code": 410, "reason": "Expired"}}
    api, _ = _api(lambda request: httpx.Response(200, content=(json.dumps(expired) + "\n").encode()))
    with pytest.raises(WatchExpired):
        list(api.watch(SPARK_APPS, "1", timeout_seconds=5))
