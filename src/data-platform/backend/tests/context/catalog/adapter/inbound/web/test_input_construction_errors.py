"""Test that a port input the web edge cannot build answers 422, like the application ValidationError."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from base import InvariantViolation, UseCaseInput
from context.catalog.adapter.inbound.web import register_error_handlers
from context.catalog.application.exceptions import ValidationError


class _ProbeUseCaseInput(UseCaseInput):
    """An input whose names field is a tuple, so a list is refused."""

    names: tuple[str, ...]


def _refusal() -> str:
    """Return the one line an InvariantViolation gives for a list in the tuple field."""
    with pytest.raises(InvariantViolation) as caught:
        _ProbeUseCaseInput(names=["a"])  # ty: ignore[invalid-argument-type]
    return str(caught.value)


def _client() -> TestClient:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/probe")
    def probe(name: str) -> dict[str, str]:
        _ProbeUseCaseInput(names=[name])  # ty: ignore[invalid-argument-type]
        return {"name": name}

    @app.get("/refused")
    def refused() -> dict[str, str]:
        raise ValidationError("bad")

    return TestClient(app, raise_server_exceptions=False)


def test_an_input_the_router_cannot_build_answers_422_with_its_line() -> None:
    """A refused input construction answers 422 with the violation's one line as detail."""
    response = _client().get("/probe", params={"name": "a"})

    assert response.status_code == 422
    assert response.json() == {"detail": _refusal()}


def test_the_refusal_has_the_validation_error_body_shape() -> None:
    """The refused input and the application ValidationError answer with the same status and body keys."""
    client = _client()

    refused_input = client.get("/probe", params={"name": "a"})
    validation_error = client.get("/refused")

    assert refused_input.status_code == validation_error.status_code == 422
    assert set(refused_input.json()) == set(validation_error.json()) == {"detail"}
