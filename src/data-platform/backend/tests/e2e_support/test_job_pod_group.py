"""Test job_pod_group, which finds the PodGroup the Spark operator made for one maintenance job."""

from __future__ import annotations

import httpx

from e2e.support import KubernetesApi, job_pod_group

PODGROUPS = "/apis/scheduling.volcano.sh/v1beta1/namespaces/lakehouse-maintenance-operations/podgroups"


def _group(name: str, owner: str | None) -> dict:
    owners = [] if owner is None else [{"kind": "SparkApplication", "name": owner}]
    return {"metadata": {"name": name, "ownerReferences": owners}, "spec": {"queue": "table-maintenance"}}


def _api(groups: list[dict], seen: list[str]) -> KubernetesApi:
    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(f"{request.method} {request.url.path}")
        return httpx.Response(200, json={"metadata": {"resourceVersion": "1"}, "items": groups})

    return KubernetesApi(httpx.Client(transport=httpx.MockTransport(handle), base_url="https://kubernetes"))


def test_the_group_the_job_owns_answers():
    """A holder (no owner), another job's group and a later attempt's group are passed over."""
    seen: list[str] = []
    mine = _group("spark-tm-rdf-x-a1-pg", "tm-rdf-x-a1")
    others = [_group("tm-e2e-holder-1-queue", None), _group("spark-tm-rdf-y-a1-pg", "tm-rdf-y-a1")]
    groups = [*others, _group("spark-tm-rdf-x-a10-pg", "tm-rdf-x-a10"), mine]
    assert job_pod_group(_api(groups, seen), "tm-rdf-x-a1") == mine
    assert seen == [f"GET {PODGROUPS}"]


def test_no_group_yet_is_none():
    """The operator makes the group a moment after the job; until then there is none."""
    assert job_pod_group(_api([_group("spark-tm-rdf-y-a1-pg", "tm-rdf-y-a1")], []), "tm-rdf-x-a1") is None
