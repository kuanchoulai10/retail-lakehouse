"""Test SparkJobWatch, which counts how many Spark jobs of one table exist at once."""

from __future__ import annotations

import json
import threading

import httpx
import pytest

from e2e.support import KubernetesApi, SparkJobWatch, wait_until

RUN_ID = "table-maintenance/run-id"


def _job(name: str, run_id: str, version: str, *, deleting: bool = False) -> dict:
    metadata: dict = {"name": name, "uid": f"uid-{name}", "resourceVersion": version, "labels": {RUN_ID: run_id}}
    if deleting:
        metadata["deletionTimestamp"] = "2026-11-24T10:00:00Z"
    return {"metadata": metadata}


def _event(kind: str, job: dict) -> dict:
    return {"type": kind, "object": job}


class _Cluster:
    """Answer the listing with ``listed`` and each watch with the next of ``streams``, then empty ones."""

    def __init__(self, listed: list[dict], streams: list[list[dict]], relisted: list[dict] | None = None) -> None:
        self._listed = listed
        self._relisted = relisted
        self._streams = streams
        self.watches = 0
        self.lists = 0
        self._lock = threading.Lock()

    def handle(self, request: httpx.Request) -> httpx.Response:
        with self._lock:
            if request.url.params.get("watch") != "true":
                self.lists += 1
                items = self._listed if self.lists == 1 or self._relisted is None else self._relisted
                return httpx.Response(200, json={"metadata": {"resourceVersion": str(10 * self.lists)}, "items": items})
            stream = self._streams[self.watches] if self.watches < len(self._streams) else []
            self.watches += 1
        return httpx.Response(200, content="".join(json.dumps(line) + "\n" for line in stream).encode())

    def api(self) -> KubernetesApi:
        return KubernetesApi(httpx.Client(transport=httpx.MockTransport(self.handle), base_url="https://kubernetes"))


def _watched(cluster: _Cluster) -> SparkJobWatch:
    watch = SparkJobWatch.start(cluster.api(), timeout_seconds=1)
    wait_until(lambda: cluster.watches > len(cluster._streams) or None, timeout=5, interval=0.01, what="streams read")
    watch.stop()
    return watch


def test_a_job_being_deleted_still_counts_until_it_is_gone():
    """A MODIFIED event with a deletionTimestamp keeps the job live, so a next job created then makes two."""
    a, b = _job("tm-rdf-a-a1", "mr-1", "11"), _job("tm-rm-b-a1", "mr-2", "13")
    cluster = _Cluster(
        [],
        [
            [
                _event("ADDED", a),
                _event("MODIFIED", _job("tm-rdf-a-a1", "mr-1", "12", deleting=True)),
                _event("ADDED", b),
            ]
        ],
    )
    watch = _watched(cluster)
    assert watch.most_at_once({"mr-1", "mr-2"}) == 2


def test_a_clean_hand_over_counts_one_and_keeps_the_order():
    """Each run's job is gone before the next one's appears; jobs of other tables are not counted."""
    a, b, other = _job("tm-rdf-a-a1", "mr-1", "11"), _job("tm-rm-b-a1", "mr-2", "13"), _job("tm-es-o-a1", "mr-9", "12")
    cluster = _Cluster(
        [],
        [
            [_event("ADDED", a), _event("ADDED", other), _event("DELETED", a)],
            [_event("ADDED", b), _event("DELETED", b)],
        ],
    )
    watch = _watched(cluster)
    assert watch.most_at_once({"mr-1", "mr-2"}) == 1
    assert watch.order({"mr-1", "mr-2"}) == ["mr-1", "mr-2"]
    assert watch.names({"mr-1", "mr-2"}) == {"mr-1": "tm-rdf-a-a1", "mr-2": "tm-rm-b-a1"}


def test_a_job_there_before_the_watch_counts_from_the_listing():
    """The listing's jobs are live from the start, so one created later makes two."""
    a, b = _job("tm-rdf-a-a1", "mr-1", "9"), _job("tm-rm-b-a1", "mr-2", "11")
    watch = _watched(_Cluster([a], [[_event("ADDED", b)]]))
    assert watch.most_at_once({"mr-1", "mr-2"}) == 2


def test_an_expired_watch_lists_again_and_settles_what_it_missed():
    """After a 410 the new listing decides: a job gone from it was deleted, a new one was added."""
    a, b = _job("tm-rdf-a-a1", "mr-1", "9"), _job("tm-rm-b-a1", "mr-2", "15")
    expired = {"type": "ERROR", "object": {"kind": "Status", "code": 410}}
    cluster = _Cluster([a], [[expired]], relisted=[b])
    watch = _watched(cluster)
    assert cluster.lists == 2
    assert watch.most_at_once({"mr-1", "mr-2"}) == 1
    assert watch.order({"mr-1", "mr-2"}) == ["mr-1", "mr-2"]


def test_a_watch_that_failed_says_so_when_stopped():
    """An error in the watching thread is raised by stop, never lost."""

    def refuse(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "forbidden"})

    watch = SparkJobWatch.start(
        KubernetesApi(httpx.Client(transport=httpx.MockTransport(refuse), base_url="https://k"))
    )
    with pytest.raises(AssertionError, match="answered 403"):
        watch.stop()
