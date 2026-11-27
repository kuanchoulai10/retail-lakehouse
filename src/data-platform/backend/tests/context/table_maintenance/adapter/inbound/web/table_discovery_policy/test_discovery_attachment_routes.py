"""Test the discovery policy attachment routes over the real services on in-memory fakes."""

from __future__ import annotations

import logging

import pytest

from tests.context.table_maintenance.adapter.inbound.web.discovery_policy_web_world import (
    DiscoveryPolicyWebWorld,
    discovery_rule,
)


@pytest.fixture
def client() -> DiscoveryPolicyWebWorld:
    """Provide a client over policies ``sales`` and ``others``, and a catalog ``iceberg`` holding ``sales.orders``."""
    world = DiscoveryPolicyWebWorld()
    world.create("sales", discovery_rule())
    world.create("others", discovery_rule("*", action="exclude"))
    world.catalog.add_table("iceberg", "sales", "orders", "u-1")
    return world


def _policy_id(client: DiscoveryPolicyWebWorld, name: str) -> str:
    return client.client.get(f"/v1/discovery-policies/{name}").json()["id"]


def _listed(client: DiscoveryPolicyWebWorld, name: str) -> list[dict]:
    response = client.client.get(f"/v1/discovery-policies/{name}/attachments")
    assert response.status_code == 200, response.text
    return response.json()["attachments"]


def test_put_attachment_answers_the_place_and_the_policy(client: DiscoveryPolicyWebWorld) -> None:
    """PUT attachments answers 200 with the place and the policy, and no id of its own."""
    response = client.attach("sales", "table", ["iceberg", "sales", "orders"])

    assert response.status_code == 200, response.text
    assert response.json() == {
        "target": {"type": "table", "path": ["iceberg", "sales", "orders"], "table_uuid": "u-1"},
        "policy_id": _policy_id(client, "sales"),
        "policy_name": "sales",
    }


def test_put_attachment_twice_replaces_the_policy_the_place_holds(client: DiscoveryPolicyWebWorld) -> None:
    """Attaching another policy to the same place replaces it."""
    client.attach("sales", "catalog", ["iceberg"])

    second = client.attach("others", "catalog", ["iceberg"]).json()

    assert second["policy_name"] == "others"
    assert _listed(client, "sales") == []
    assert [a["target"]["path"] for a in _listed(client, "others")] == [["iceberg"]]


def test_put_attachment_in_a_refused_catalog_is_403(client: DiscoveryPolicyWebWorld) -> None:
    """A catalog the credential cannot read answers 403 naming it, and nothing is stored."""
    client.catalog.deny("iceberg")

    response = client.attach("sales", "namespace", ["iceberg", "sales"])

    assert response.status_code == 403
    assert response.json()["detail"] == "the platform's catalog credential cannot read catalog iceberg"
    assert client.namespaces.list_in_catalog("iceberg") == []


def test_put_attachment_to_a_namespace_level_holding_a_dot_is_422(client: DiscoveryPolicyWebWorld) -> None:
    """A namespace level with a dot in it could never apply to a table, so the attach is refused."""
    client.catalog.add_namespace("iceberg", "eu.west")

    response = client.attach("sales", "namespace", ["iceberg", "eu.west"])

    assert response.status_code == 422
    assert "namespace level 'eu.west' holds a '.'" in response.json()["detail"]
    assert client.namespaces.list_in_catalog("iceberg") == []


@pytest.mark.parametrize(
    ("name", "type_", "path"),
    [
        ("sales", "catalog", ["nope"]),
        ("sales", "namespace", ["iceberg", "ghost"]),
        ("sales", "table", ["iceberg", "sales", "ghost"]),
        ("ghost", "catalog", ["iceberg"]),
    ],
)
def test_put_attachment_to_a_missing_target_or_policy_is_404(
    client: DiscoveryPolicyWebWorld, name: str, type_: str, path: list[str]
) -> None:
    """A place or a policy that does not exist answers 404, and nothing is stored."""
    assert client.attach(name, type_, path).status_code == 404
    assert client.catalogs.list_all() == []
    assert client.namespaces.list_all() == []
    assert client.tables.list_all() == []


def test_put_attachment_with_an_extra_field_is_422(client: DiscoveryPolicyWebWorld) -> None:
    """The request refuses fields it does not know."""
    response = client.client.put(
        "/v1/discovery-policies/sales/attachments",
        json={"target": {"type": "catalog", "path": ["iceberg"], "table_uuid": "u-1"}},
    )

    assert response.status_code == 422


def test_get_attachments_lists_places_by_type_and_marks_orphans(client: DiscoveryPolicyWebWorld) -> None:
    """GET lists catalogs, then namespaces, then tables; a place that is gone is orphaned.

    A table table maintenance still records is not orphaned: the scan that finds it gone drops it, and
    dropping it takes its policy off.
    """
    table = client.attach("sales", "table", ["iceberg", "sales", "orders"]).json()
    namespace = client.attach("sales", "namespace", ["iceberg", "sales"]).json()
    catalog = client.attach("sales", "catalog", ["iceberg"]).json()
    client.catalog.drop_namespace("iceberg", "sales")

    assert _listed(client, "sales") == [
        {**catalog, "orphaned": False},
        {**namespace, "orphaned": True},
        {**table, "orphaned": False},
    ]


def test_get_attachments_in_a_refused_catalog_stays_200_and_not_orphaned(client: DiscoveryPolicyWebWorld) -> None:
    """A catalog the credential cannot read does not fail the list, and its places are not orphaned."""
    client.attach("sales", "namespace", ["iceberg", "sales"])
    client.catalog.deny("iceberg")

    assert [a["orphaned"] for a in _listed(client, "sales")] == [False]


def test_get_attachments_of_an_unknown_policy_is_404(client: DiscoveryPolicyWebWorld) -> None:
    """Listing the attachments of a policy that does not exist answers 404."""
    assert client.client.get("/v1/discovery-policies/ghost/attachments").status_code == 404


def test_delete_attachment_answers_204_and_frees_the_policy(client: DiscoveryPolicyWebWorld) -> None:
    """DELETE by place answers 204 with no body; the policy, no longer attached, can then be deleted."""
    client.attach("sales", "catalog", ["iceberg"])
    assert client.client.delete("/v1/discovery-policies/sales").status_code == 409

    response = client.detach("sales", "catalog", ["iceberg"])

    assert (response.status_code, response.content) == (204, b"")
    assert _listed(client, "sales") == []
    assert client.client.delete("/v1/discovery-policies/sales").status_code == 204


def test_delete_attachment_twice_is_404_the_second_time(client: DiscoveryPolicyWebWorld) -> None:
    """The second identical detach finds the place holding no policy: 404."""
    client.attach("sales", "table", ["iceberg", "sales", "orders"])

    first = client.detach("sales", "table", ["iceberg", "sales", "orders"])
    second = client.detach("sales", "table", ["iceberg", "sales", "orders"])

    assert (first.status_code, second.status_code) == (204, 404)


def test_delete_attachment_of_a_dropped_catalog_is_204(client: DiscoveryPolicyWebWorld) -> None:
    """A policy whose catalog is gone is detached by its path, without reading the catalog."""
    client.attach("sales", "catalog", ["iceberg"])
    client.catalog.drop_catalog("iceberg")

    assert client.detach("sales", "catalog", ["iceberg"]).status_code == 204


def test_delete_attachment_answers_204_when_the_scan_request_fails(
    client: DiscoveryPolicyWebWorld, caplog: pytest.LogCaptureFixture
) -> None:
    """A detach whose scan request fails is still stored, answers 204 and logs."""
    client.attach("sales", "catalog", ["iceberg"])
    client.requests.failing.add("iceberg")

    with caplog.at_level(logging.WARNING):
        response = client.detach("sales", "catalog", ["iceberg"])

    assert response.status_code == 204
    assert _listed(client, "sales") == []
    assert "could not request a discovery of catalog iceberg" in caplog.text


@pytest.mark.parametrize(
    ("type_", "path"),
    [("schema", ["iceberg"]), ("table", ["iceberg", "orders"])],
)
def test_delete_with_a_bad_place_is_422(client: DiscoveryPolicyWebWorld, type_: str, path: list[str]) -> None:
    """An unknown target type, or a table path without a namespace, answers 422."""
    assert client.detach("sales", type_, path).status_code == 422


def test_delete_without_a_path_is_422(client: DiscoveryPolicyWebWorld) -> None:
    """The place must be named: a DELETE with no ``path`` answers 422."""
    response = client.client.delete("/v1/discovery-policies/sales/attachments", params={"target_type": "catalog"})

    assert response.status_code == 422


def test_delete_of_another_policys_attachment_is_404(client: DiscoveryPolicyWebWorld) -> None:
    """A place holding another policy answers 404 and keeps it."""
    client.attach("others", "catalog", ["iceberg"])

    response = client.detach("sales", "catalog", ["iceberg"])

    assert response.status_code == 404
    assert response.json()["detail"].startswith(f"discovery policy {_policy_id(client, 'sales')} is not attached")
    assert [a["target"]["path"] for a in _listed(client, "others")] == [["iceberg"]]
