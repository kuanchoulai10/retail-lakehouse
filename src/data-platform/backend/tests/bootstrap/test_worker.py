"""Test the worker process: startup, shutdown on a stop request or SIGTERM and bridge cleanup."""

from __future__ import annotations

import asyncio
import os
import signal
from typing import TYPE_CHECKING, Any, Self
from unittest.mock import MagicMock

import pytest

from bootstrap.container import build_repositories, build_use_cases
from bootstrap.worker import run_worker
from tests.bootstrap.container.container_support import (
    NOW,
    fake_gateways,
    sqlite_engine,
    sqlite_settings,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


class FakeBridge:
    """Async loop bridge stub that records when it is closed."""

    def __init__(self) -> None:
        """Start with the bridge open."""
        self.closed = False

    def close(self) -> None:
        """Mark the bridge as closed."""
        self.closed = True


class FakeWorker:
    """Temporal worker stub that records entering and shutting down."""

    def __init__(self, on_enter: Callable[[], None]) -> None:
        """Hold the callback to run when the worker is entered."""
        self.on_enter = on_enter
        self.entered = False
        self.shut_down = False

    async def __aenter__(self) -> Self:
        """Mark the worker as entered and schedule the callback on the running loop."""
        self.entered = True
        asyncio.get_running_loop().call_soon(self.on_enter)
        return self

    async def __aexit__(self, *_: object) -> None:
        """Mark the worker as shut down."""
        self.shut_down = True


class Harness:
    """Collaborators that let run_worker execute with fakes instead of Temporal and Kubernetes."""

    def __init__(self, on_enter: Callable[[], None] | None = None) -> None:
        """Create the fake bridge and worker and the counters for the calls made."""
        self.bridge = FakeBridge()
        self.stop_callbacks: list[Callable[[], None]] = []
        self.k8s_built = 0
        self.startups: list[Any] = []
        self.worker = FakeWorker(on_enter or self._stop)
        self.worker_kwargs: dict[str, Any] = {}

    def _stop(self) -> None:
        for callback in self.stop_callbacks:
            callback()

    def install_stop(self, callback: Callable[[], None]) -> None:
        """Record the stop callback instead of installing signal handlers."""
        self.stop_callbacks.append(callback)

    def k8s_api_factory(self) -> MagicMock:
        """Count the Kubernetes API builds and return a mock."""
        self.k8s_built += 1
        return MagicMock(name="k8s")

    def use_cases_builder(self, settings: Any, bridge: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        """Build use cases on SQLite with fake gateways, checking it gets the harness bridge."""
        assert bridge is self.bridge
        kwargs["k8s_api_factory"]()
        return build_use_cases(build_repositories(sqlite_engine()), fake_gateways(), clock=lambda: NOW)

    async def connect(self, _: Any) -> MagicMock:  # noqa: ANN401
        """Return a mock Temporal client without connecting."""
        return MagicMock(name="worker-client")

    async def startup(self, *args: Any) -> None:  # noqa: ANN401
        """Record a startup call."""
        self.startups.append(args)

    def worker_builder(self, *args: Any, **kwargs: Any) -> FakeWorker:  # noqa: ANN401
        """Return the fake worker instead of building a real one."""
        self.worker_kwargs = kwargs
        return self.worker

    def run(self, **overrides: Any) -> None:  # noqa: ANN401
        """Run the worker process with the harness collaborators and optional overrides."""
        options: dict[str, Any] = {
            "bridge_factory": lambda: self.bridge,
            "use_cases_builder": self.use_cases_builder,
            "k8s_api_factory": self.k8s_api_factory,
            "connect": self.connect,
            "startup": self.startup,
            "worker_builder": self.worker_builder,
            "install_stop": self.install_stop,
            **overrides,
        }
        options = {k: v for k, v in options.items() if v is not None}
        asyncio.run(run_worker(sqlite_settings(), **options))


def test_stop_request_shuts_the_worker_down_and_closes_the_bridge():
    """A stop request enters the worker once, shuts it down and closes the bridge."""
    harness = Harness()

    harness.run()

    assert harness.k8s_built == 1
    assert len(harness.startups) == 1
    assert harness.worker.entered is True
    assert harness.worker.shut_down is True
    assert harness.bridge.closed is True
    assert harness.worker_kwargs["max_concurrent_activities"] == 16


def test_sigterm_shuts_the_worker_down_and_closes_the_bridge():
    """SIGTERM shuts the worker down and closes the bridge."""
    harness = Harness(on_enter=lambda: os.kill(os.getpid(), signal.SIGTERM))
    harness.run(install_stop=None)

    assert harness.worker.shut_down is True
    assert harness.bridge.closed is True


def test_bridge_is_closed_when_startup_fails():
    """A startup failure propagates, the worker is never entered and the bridge is closed."""
    harness = Harness()

    async def failing_startup(*_: Any) -> None:  # noqa: ANN401
        raise RuntimeError("temporal down")

    with pytest.raises(RuntimeError, match="temporal down"):
        harness.run(startup=failing_startup)

    assert harness.worker.entered is False
    assert harness.bridge.closed is True


@pytest.fixture(autouse=True)
def _restore_signal_handlers() -> Iterator[None]:
    saved = {s: signal.getsignal(s) for s in (signal.SIGTERM, signal.SIGINT)}
    yield
    for signum, handler in saved.items():
        signal.signal(signum, handler)
