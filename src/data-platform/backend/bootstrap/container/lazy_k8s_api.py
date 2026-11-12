"""Provide the LazyK8sApi proxy."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class LazyK8sApi:
    """Proxy a client that is built on first use, at most once: a Kubernetes API (custom objects, core, ...).

    Loading a kubeconfig at construction would stop the API and the event consumer
    from starting where no cluster config exists; only Spark calls need one. The
    Spark event log file system is deferred the same way.
    """

    def __init__(self, factory: Callable[[], object]) -> None:
        """Store the factory without calling it."""
        self._factory = factory
        self._api: object | None = None
        self._lock = threading.Lock()

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401
        """Build the real API on first access, then delegate to it."""
        if name.startswith("_"):
            raise AttributeError(name)
        with self._lock:
            if self._api is None:
                self._api = self._factory()
            api = self._api
        return getattr(api, name)
