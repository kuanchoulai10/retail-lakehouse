"""Test ensure_principal, which gives the e2e its own Polaris principal before the scenarios run."""

from __future__ import annotations

import json

import httpx
import pytest

from e2e.setup_principal import ensure_principal, main
from e2e.support import PolarisClient

CALLS = [
    ("POST", "/principals", {"principal": {"name": "tm-e2e"}, "credentialRotationRequired": False}),
    ("POST", "/principal-roles", {"principalRole": {"name": "tm_e2e"}}),
    ("POST", "/catalogs/iceberg/catalog-roles", {"catalogRole": {"name": "tm_e2e"}}),
    (
        "PUT",
        "/catalogs/iceberg/catalog-roles/tm_e2e/grants",
        {"grant": {"type": "catalog", "privilege": "CATALOG_MANAGE_CONTENT"}},
    ),
    ("PUT", "/principal-roles/tm_e2e/catalog-roles/iceberg", {"catalogRole": {"name": "tm_e2e"}}),
    ("PUT", "/principals/tm-e2e/principal-roles", {"principalRole": {"name": "tm_e2e"}}),
    ("PUT", "/principals/tm-e2e/principal-roles", {"principalRole": {"name": "service_admin"}}),
    ("POST", "/principals/tm-e2e/reset", {}),
]
ROTATED = {"principal": {"name": "tm-e2e"}, "credentials": {"clientId": "e2e-id", "clientSecret": "e2e-secret"}}


def _polaris(answer) -> tuple[PolarisClient, list[tuple[str, str, object]]]:
    seen: list[tuple[str, str, object]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth/tokens"):
            return httpx.Response(200, json={"access_token": "platform-token"})
        path = request.url.path.removeprefix("/api/management/v1")
        body = json.loads(request.content) if request.content else None
        seen.append((request.method, path, body))
        return answer(request.method, path)

    client = PolarisClient(
        httpx.Client(transport=httpx.MockTransport(handle)),
        catalog_uri="http://polaris:8181/api/catalog",
        management_uri="http://polaris:8181/api/management/v1",
        credential="root:root-secret",
        scope="PRINCIPAL_ROLE:ALL",
    )
    return client, seen


def test_a_fresh_polaris_gets_the_principal_its_roles_and_grant_then_reset_credentials():
    """Every piece is created and assigned in order, and the reset credentials come back."""

    def answer(method: str, path: str) -> httpx.Response:
        if path.endswith("/reset"):
            return httpx.Response(200, json=ROTATED)
        return httpx.Response(201, json={})

    polaris, seen = _polaris(answer)
    assert ensure_principal(polaris, catalog="iceberg") == "e2e-id:e2e-secret"
    assert seen == CALLS


def test_what_already_exists_is_kept_and_the_credentials_are_still_reset():
    """A second run finds the principal and roles (409) and only resets the credentials."""

    def answer(method: str, path: str) -> httpx.Response:
        if path.endswith("/reset"):
            return httpx.Response(200, json=ROTATED)
        if method == "POST":
            return httpx.Response(409, json={"error": {"message": "already exists"}})
        return httpx.Response(201, json={})

    polaris, seen = _polaris(answer)
    assert ensure_principal(polaris, catalog="iceberg") == "e2e-id:e2e-secret"
    assert [(method, path) for method, path, _ in seen] == [(method, path) for method, path, _ in CALLS]


def test_another_failure_stops_naming_the_call_and_polaris_message():
    """A refused grant is not taken for "exists": the setup fails, saying which call and why."""

    def answer(method: str, path: str) -> httpx.Response:
        if path.endswith("/grants"):
            return httpx.Response(500, json={"error": {"message": "boom"}})
        return httpx.Response(201, json={})

    polaris, seen = _polaris(answer)
    with pytest.raises(RuntimeError, match=r"PUT /catalogs/iceberg/catalog-roles/tm_e2e/grants answered 500: boom"):
        ensure_principal(polaris, catalog="iceberg")
    assert not any(path.endswith("/reset") for _, path, _ in seen)


def test_main_writes_the_credentials_for_the_owner_only_and_prints_no_secret(tmp_path, capsys):
    """The scenarios read the file; nobody else may, and the log holds no credential."""

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth/tokens"):
            return httpx.Response(200, json={"access_token": "platform-token"})
        if request.url.path.endswith("/reset"):
            return httpx.Response(200, json=ROTATED)
        return httpx.Response(201, json={})

    target = tmp_path / "polaris"
    main(
        {
            "E2E_POLARIS_CREDENTIAL_FILE": str(target),
            "GLAC_CATALOG__URI": "http://polaris:8181/api/catalog",
            "GLAC_CATALOG__MANAGEMENT_URI": "http://polaris:8181/api/management/v1",
            "GLAC_CATALOG__CREDENTIAL": "root:root-secret",
            "GLAC_CATALOG__SCOPE": "PRINCIPAL_ROLE:ALL",
            "E2E_CATALOG": "iceberg",
        },
        http_factory=lambda: httpx.Client(transport=httpx.MockTransport(handle)),
    )
    assert target.read_text() == "e2e-id:e2e-secret"
    assert target.stat().st_mode & 0o777 == 0o600
    printed = capsys.readouterr().out
    assert "e2e-secret" not in printed
    assert "root-secret" not in printed
