"""Share the stub use case and the client builder for the web API tests."""

from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime
from typing import Any

from adapter.inbound.web import create_app, WebUseCases
from fastapi.testclient import TestClient

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)


class StubUseCase:
    """Record each request and return a canned output or raise a canned error."""

    def __init__(self, result: Any = None, error: Exception | None = None) -> None:  # noqa: ANN401
        """Store the canned output or error."""
        self.result = result
        self.error = error
        self.requests: list[Any] = []

    def execute(self, request: Any) -> Any:  # noqa: ANN401
        """Record the request, then raise or return the canned value."""
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.result


def build_client(**use_cases: Any) -> TestClient:  # noqa: ANN401
    """Build a client; every use case not given is an empty stub."""
    unknown = set(use_cases) - {f.name for f in fields(WebUseCases)}
    if unknown:
        raise TypeError(f"unknown use cases: {sorted(unknown)}")
    values: dict[str, Any] = {
        f.name: use_cases.get(f.name, StubUseCase()) for f in fields(WebUseCases)
    }
    return TestClient(create_app(WebUseCases(**values)))
