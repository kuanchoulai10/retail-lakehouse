"""Provide SparkJobWatch, which records each maintenance Spark job's life to count a table's jobs at once."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from e2e.support.watch_expired import WatchExpired

if TYPE_CHECKING:
    from e2e.support.kubernetes_api import KubernetesApi

SPARK_APPLICATIONS = "/apis/sparkoperator.k8s.io/v1beta2/namespaces/lakehouse-maintenance-operations/sparkapplications"
RUN_ID = "table-maintenance/run-id"
_ADDED, _DELETED = "added", "deleted"


class SparkJobWatch:
    """Watch the maintenance SparkApplications in a thread and keep the order they appeared and went in.

    A job is live from its first sighting (listed, ADDED or MODIFIED) until DELETED, so one being
    deleted (a ``deletionTimestamp`` set) still counts. A job carries no table label, so the counts
    take the table's run ids, which the platform knows before the first job is submitted.
    """

    def __init__(self, kubernetes: KubernetesApi, timeout_seconds: int) -> None:
        """Watch through ``kubernetes``; each watch call ends after ``timeout_seconds`` so stop is prompt."""
        self._kubernetes = kubernetes
        self._timeout_seconds = timeout_seconds
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._timeline: list[tuple[str, str, str, str]] = []
        self._live: dict[str, tuple[str, str]] = {}
        self._error: BaseException | None = None
        self._thread = threading.Thread(target=self._run, name="spark-job-watch", daemon=True)

    @classmethod
    def start(cls, kubernetes: KubernetesApi, *, timeout_seconds: int = 5) -> SparkJobWatch:
        """Start watching now; jobs that exist already count from the first listing."""
        watch = cls(kubernetes, timeout_seconds)
        watch._thread.start()
        return watch

    def stop(self) -> None:
        """Stop the thread and raise what made it fail, if anything did. Stopping twice is fine."""
        self._stop.set()
        self._thread.join(timeout=self._timeout_seconds + 60)
        assert not self._thread.is_alive(), "the Spark job watch did not stop"
        if self._error is not None:
            raise self._error

    def most_at_once(self, run_ids: set[str]) -> int:
        """Return the most jobs of these runs that were live at the same time."""
        live: set[str] = set()
        most = 0
        for kind, uid, _, _ in self._events(run_ids):
            if kind == _ADDED:
                live.add(uid)
            else:
                live.discard(uid)
            most = max(most, len(live))
        return most

    def order(self, run_ids: set[str]) -> list[str]:
        """Return these runs' ids in the order their first job appeared."""
        seen: list[str] = []
        for kind, _, run_id, _ in self._events(run_ids):
            if kind == _ADDED and run_id not in seen:
                seen.append(run_id)
        return seen

    def names(self, run_ids: set[str]) -> dict[str, str]:
        """Return each of these runs' last job name."""
        return {run_id: name for kind, _, run_id, name in self._events(run_ids) if kind == _ADDED}

    def _events(self, run_ids: set[str]) -> list[tuple[str, str, str, str]]:
        with self._lock:
            return [event for event in self._timeline if event[2] in run_ids]

    def _run(self) -> None:
        try:
            version = self._relist()
            while not self._stop.is_set():
                try:
                    for event in self._kubernetes.watch(
                        SPARK_APPLICATIONS, version, label_selector=RUN_ID, timeout_seconds=self._timeout_seconds
                    ):
                        version = event["object"]["metadata"]["resourceVersion"]
                        if event["type"] == "DELETED":
                            self._went(event["object"]["metadata"]["uid"])
                        elif event["type"] in ("ADDED", "MODIFIED"):
                            self._appeared(event["object"])
                except WatchExpired:
                    version = self._relist()
        except BaseException as error:  # noqa: BLE001
            self._error = error

    def _relist(self) -> str:
        listing = self._kubernetes.list(SPARK_APPLICATIONS, label_selector=RUN_ID)
        listed = {item["metadata"]["uid"] for item in listing["items"]}
        for uid in [uid for uid in self._live if uid not in listed]:
            self._went(uid)
        for item in listing["items"]:
            self._appeared(item)
        return listing["metadata"]["resourceVersion"]

    def _appeared(self, job: dict[str, Any]) -> None:
        metadata = job["metadata"]
        if metadata["uid"] in self._live:
            return
        run_id, name = metadata.get("labels", {}).get(RUN_ID, ""), metadata["name"]
        with self._lock:
            self._live[metadata["uid"]] = (run_id, name)
            self._timeline.append((_ADDED, metadata["uid"], run_id, name))

    def _went(self, uid: str) -> None:
        if uid not in self._live:
            return
        with self._lock:
            run_id, name = self._live.pop(uid)
            self._timeline.append((_DELETED, uid, run_id, name))
