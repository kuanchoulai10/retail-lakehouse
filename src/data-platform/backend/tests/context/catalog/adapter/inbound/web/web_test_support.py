"""Share the stub use case and the app and client builders for the catalog web API tests."""

from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from context.catalog.adapter.inbound.web import register_routes
from context.catalog.adapter.inbound.web.shared import WebUseCases

NOW = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)


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


def build_app(**use_cases: Any) -> FastAPI:  # noqa: ANN401
    """Build an app with the catalog routes; every use case not given is an empty stub."""
    unknown = set(use_cases) - {f.name for f in fields(WebUseCases)}
    if unknown:
        raise TypeError(f"unknown use cases: {sorted(unknown)}")
    values: dict[str, Any] = {f.name: use_cases.get(f.name, StubUseCase()) for f in fields(WebUseCases)}
    app = FastAPI()
    register_routes(app, WebUseCases(**values))
    return app


def build_client(**use_cases: Any) -> TestClient:  # noqa: ANN401
    """Build a test client over ``build_app``."""
    return TestClient(build_app(**use_cases))
