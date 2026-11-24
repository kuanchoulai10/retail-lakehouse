"""Test drop_catalog, which removes whatever a scenario left of a catalog it created."""

from __future__ import annotations

import httpx
import pytest

from e2e.support import PolarisClient, drop_catalog

CATALOG = "/api/catalog"
MANAGEMENT = "/api/management/v1"


def _polaris(answer) -> tuple[PolarisClient, list[tuple[str, str]]]:
    seen: list[tuple[str, str]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth/tokens"):
            return httpx.Response(200, json={"access_token": "token"})
        target = request.url.raw_path.decode()
        seen.append((request.method, target))
        return answer(request.method, target)

    client = PolarisClient(
        httpx.Client(transport=httpx.MockTransport(handle)),
        catalog_uri="http://polaris:8181" + CATALOG,
        management_uri="http://polaris:8181" + MANAGEMENT,
        credential="e2e-id:e2e-secret",
        scope="PRINCIPAL_ROLE:ALL",
    )
    return client, seen


def test_a_catalog_already_gone_is_left_alone():
    """A 404 for the catalog means nothing is left: no other call is made."""
    polaris, seen = _polaris(lambda method, target: httpx.Response(404, json={}))
    drop_catalog(polaris, "rt")
    assert seen == [("GET", MANAGEMENT + "/catalogs/rt")]


def test_everything_left_is_deleted_children_first_then_the_roles_and_the_catalog():
    """Views, generic tables and tables of each namespace go first, deepest namespace first."""
    listings = {
        CATALOG + "/v1/rt/namespaces": {"namespaces": [["a"]]},
        CATALOG + "/v1/rt/namespaces?parent=a": {"namespaces": [["a", "b.c"]]},
        CATALOG + "/v1/rt/namespaces?parent=a%1Fb.c": {"namespaces": []},
        CATALOG + "/v1/rt/namespaces/a%1Fb.c/views": {"identifiers": [{"name": "v"}]},
        CATALOG + "/polaris/v1/rt/namespaces/a%1Fb.c/generic-tables": {"identifiers": [{"name": "g"}]},
        CATALOG + "/v1/rt/namespaces/a%1Fb.c/tables": {"identifiers": [{"name": "t"}]},
        MANAGEMENT + "/catalogs/rt/catalog-roles": {"roles": [{"name": "catalog_admin"}, {"name": "reader"}]},
    }

    def answer(method: str, target: str) -> httpx.Response:
        if method == "GET":
            return httpx.Response(200, json=listings.get(target, {"identifiers": []}))
        return httpx.Response(204)

    polaris, seen = _polaris(answer)
    drop_catalog(polaris, "rt")
    assert [call for call in seen if call[0] == "DELETE"] == [
        ("DELETE", CATALOG + "/v1/rt/namespaces/a%1Fb.c/views/v"),
        ("DELETE", CATALOG + "/polaris/v1/rt/namespaces/a%1Fb.c/generic-tables/g"),
        ("DELETE", CATALOG + "/v1/rt/namespaces/a%1Fb.c/tables/t?purgeRequested=false"),
        ("DELETE", CATALOG + "/v1/rt/namespaces/a%1Fb.c"),
        ("DELETE", CATALOG + "/v1/rt/namespaces/a"),
        ("DELETE", MANAGEMENT + "/catalogs/rt/catalog-roles/reader"),
        ("DELETE", MANAGEMENT + "/catalogs/rt"),
    ]


def test_a_catalog_polaris_will_not_delete_fails_with_its_answer():
    """The cleanup reports a catalog left behind instead of passing silently."""

    def answer(method: str, target: str) -> httpx.Response:
        if method == "DELETE":
            return httpx.Response(400, json={"error": {"message": "catalog not empty"}})
        return httpx.Response(200, json={})

    polaris, _ = _polaris(answer)
    with pytest.raises(RuntimeError, match=r"catalog rt was not dropped: 400 .*catalog not empty"):
        drop_catalog(polaris, "rt")
