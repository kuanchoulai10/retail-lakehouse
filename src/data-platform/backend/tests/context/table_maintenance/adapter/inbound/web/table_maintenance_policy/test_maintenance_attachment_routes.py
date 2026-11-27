"""Test the maintenance policy attachment routes over the real services on in-memory fakes."""

from __future__ import annotations

import pytest

from tests.context.table_maintenance.adapter.inbound.web.policy_web_world import PolicyWebWorld


@pytest.fixture
def world() -> PolicyWebWorld:
    """Provide a client over the default policy, a gold policy and one managed table prod.sales.eu.orders."""
    world = PolicyWebWorld()
    world.create("gold")
    return world


def _gold_id(world: PolicyWebWorld) -> str:
    return world.client.get("/v1/maintenance-policies/gold").json()["id"]


def _listed(world: PolicyWebWorld, name: str = "gold") -> list[dict]:
    response = world.client.get(f"/v1/maintenance-policies/{name}/attachments")
    assert response.status_code == 200, response.text
    return response.json()["attachments"]


def _held(world: PolicyWebWorld) -> list[str | None]:
    places = [*world.catalogs.list_all(), *world.namespaces.list_all(), *world.tables.list_all()]
    return [None if p.maintenance_policy_id is None else p.maintenance_policy_id.value for p in places]


def test_put_attachment_answers_the_place_and_the_policy(world: PolicyWebWorld) -> None:
    """PUT attachments answers 200 with the place and the policy, and no id or time of its own."""
    response = world.attach("gold", "namespace", ["prod", "sales"])

    assert response.status_code == 200, response.text
    assert response.json() == {
        "target": {"type": "namespace", "path": ["prod", "sales"], "table_uuid": None},
        "policy_id": _gold_id(world),
        "policy_name": "gold",
    }


def test_put_attachment_wakes_the_table(world: PolicyWebWorld) -> None:
    """Attaching tells the table whose applicable policy changed."""
    world.attach("gold", "namespace", ["prod", "sales"])

    assert [(c.table_uuid, c.change) for c in world.changes.calls] == [("u-1", "policy_changed")]


def test_put_attachment_twice_replaces_the_policy_the_place_holds(world: PolicyWebWorld) -> None:
    """Attaching another policy to the same place replaces it."""
    world.attach("gold", "catalog", ["prod"])

    second = world.attach("default", "catalog", ["prod"]).json()

    assert second["policy_name"] == "default"
    assert _listed(world) == []
    assert [a["target"]["path"] for a in _listed(world, "default")] == [["prod"]]


def test_put_attachment_to_a_table_resolves_its_uuid(world: PolicyWebWorld) -> None:
    """A table target's path is catalog, namespace levels and table; the answer carries its uuid."""
    response = world.attach("gold", "table", ["prod", "sales", "eu", "orders"])
    assert response.status_code == 200, response.text
    assert response.json()["target"]["table_uuid"] == "u-1"


def test_put_attachment_to_a_namespace_level_holding_a_dot_is_422(world: PolicyWebWorld) -> None:
    """A level holding a dot could never apply to a table, so it is refused with 422 and nothing is stored."""
    world.catalog.add_namespace("prod", "eu.west")

    response = world.attach("gold", "namespace", ["prod", "eu.west"])

    assert response.status_code == 422
    assert "holds a '.'" in response.json()["detail"]
    assert world.namespaces.list_all() == []


@pytest.mark.parametrize(
    ("type_", "path"),
    [
        ("table", ["prod", "sales", "eu", "ghost"]),
        ("namespace", ["prod", "missing"]),
        ("catalog", ["nope"]),
    ],
)
def test_put_attachment_to_a_target_missing_from_the_catalog_is_404(
    world: PolicyWebWorld, type_: str, path: list[str]
) -> None:
    """A table, namespace or catalog missing from the catalog answers 404 and nothing is attached."""
    assert world.attach("gold", type_, path).status_code == 404
    assert _held(world) == [None]


def test_put_attachment_of_an_unknown_policy_is_404(world: PolicyWebWorld) -> None:
    """Attaching a policy that does not exist answers 404."""
    assert world.attach("nope", "catalog", ["prod"]).status_code == 404


def test_put_attachment_with_a_bad_target_type_is_422(world: PolicyWebWorld) -> None:
    """An unknown target type answers 422."""
    assert world.attach("gold", "table-like", ["prod", "sales", "orders"]).status_code == 422


def test_put_attachment_with_an_extra_field_is_422(world: PolicyWebWorld) -> None:
    """The request refuses fields it does not know, a table uuid among them."""
    response = world.client.put(
        "/v1/maintenance-policies/gold/attachments",
        json={"target": {"type": "catalog", "path": ["prod"], "table_uuid": "u-1"}},
    )

    assert response.status_code == 422


def test_put_attachment_in_a_refused_catalog_is_403(world: PolicyWebWorld) -> None:
    """Attaching in a catalog the credential cannot read answers 403 naming it, and nothing is attached."""
    world.catalog.deny("prod")
    response = world.attach("gold", "catalog", ["prod"])
    assert response.status_code == 403
    assert response.json() == {"detail": "the platform's catalog credential cannot read catalog prod"}
    assert world.catalogs.list_all() == []


def test_get_attachments_lists_places_by_type_and_marks_orphans(world: PolicyWebWorld) -> None:
    """GET attachments lists the policy's places by type and then path; a place that is gone is orphaned."""
    world.attach("gold", "namespace", ["prod", "sales", "eu"])
    world.attach("gold", "namespace", ["prod", "sales"])
    world.attach("gold", "catalog", ["prod"])
    world.catalog.drop_table("prod", "sales.eu", "orders")
    world.catalog.drop_namespace("prod", "sales.eu")

    gold = _gold_id(world)
    assert _listed(world) == [
        {
            "target": {"type": "catalog", "path": ["prod"], "table_uuid": None},
            "policy_id": gold,
            "policy_name": "gold",
            "orphaned": False,
        },
        {
            "target": {"type": "namespace", "path": ["prod", "sales"], "table_uuid": None},
            "policy_id": gold,
            "policy_name": "gold",
            "orphaned": False,
        },
        {
            "target": {"type": "namespace", "path": ["prod", "sales", "eu"], "table_uuid": None},
            "policy_id": gold,
            "policy_name": "gold",
            "orphaned": True,
        },
    ]


def test_get_attachments_in_a_refused_catalog_stays_200_and_not_orphaned(world: PolicyWebWorld) -> None:
    """A catalog the credential cannot read does not fail the list; its place is not orphaned."""
    world.attach("gold", "catalog", ["prod"])
    world.catalog.deny("prod")
    assert [a["orphaned"] for a in _listed(world)] == [False]


def test_get_attachments_of_an_unknown_policy_is_404(world: PolicyWebWorld) -> None:
    """GET attachments of a policy that does not exist answers 404, like GET and DELETE of the same name."""
    assert world.client.get("/v1/maintenance-policies/nope/attachments").status_code == 404


def test_delete_attachment_by_location_answers_204_and_wakes_the_table(world: PolicyWebWorld) -> None:
    """DELETE names the place by ``target_type`` and repeated ``path``; it answers 204 and tells the table."""
    world.attach("gold", "namespace", ["prod", "sales"])
    world.changes.calls.clear()

    response = world.client.delete(
        "/v1/maintenance-policies/gold/attachments?target_type=namespace&path=prod&path=sales"
    )

    assert (response.status_code, response.content) == (204, b"")
    assert _listed(world) == []
    assert [(c.table_uuid, c.change) for c in world.changes.calls] == [("u-1", "policy_changed")]


def test_delete_from_a_table_by_location(world: PolicyWebWorld) -> None:
    """A table is named by its path; the row holding the policy lets go of it."""
    world.attach("gold", "table", ["prod", "sales", "eu", "orders"])

    assert world.detach("gold", "table", ["prod", "sales", "eu", "orders"]).status_code == 204
    assert _held(world) == [None]


def test_delete_attachment_twice_is_404_the_second_time(world: PolicyWebWorld) -> None:
    """Once detached the place no longer holds the policy."""
    world.attach("gold", "catalog", ["prod"])
    assert world.detach("gold", "catalog", ["prod"]).status_code == 204

    assert world.detach("gold", "catalog", ["prod"]).status_code == 404


def test_delete_an_orphaned_place_is_204(world: PolicyWebWorld) -> None:
    """A place whose table and catalog are gone is detached by location, without reading the catalog."""
    world.attach("gold", "table", ["prod", "sales", "eu", "orders"])
    world.catalog.drop_catalog("prod")

    assert world.detach("gold", "table", ["prod", "sales", "eu", "orders"]).status_code == 204
    assert _held(world) == [None]


def test_delete_attachment_in_a_refused_catalog_is_204(world: PolicyWebWorld) -> None:
    """Detaching does not read the catalog, so a catalog the credential cannot read does not stop it."""
    world.attach("gold", "namespace", ["prod", "sales"])
    world.catalog.deny("prod")

    assert world.detach("gold", "namespace", ["prod", "sales"]).status_code == 204
    assert _listed(world) == []


@pytest.mark.parametrize(("type_", "path"), [("warehouse", ["prod"]), ("table", ["prod", "orders"])])
def test_delete_with_a_bad_place_is_422(world: PolicyWebWorld, type_: str, path: list[str]) -> None:
    """An unknown target type, or a path naming no place of its type, answers 422."""
    assert world.detach("gold", type_, path).status_code == 422


def test_delete_without_a_path_is_422(world: PolicyWebWorld) -> None:
    """The place's path is required."""
    response = world.client.delete("/v1/maintenance-policies/gold/attachments?target_type=catalog")

    assert response.status_code == 422


def test_delete_through_an_unknown_policy_is_404(world: PolicyWebWorld) -> None:
    """Detaching through a policy that does not exist answers 404 and keeps what is held."""
    world.attach("gold", "catalog", ["prod"])

    assert world.detach("nope", "catalog", ["prod"]).status_code == 404
    assert len(_listed(world)) == 1


def test_delete_of_another_policys_place_is_404(world: PolicyWebWorld) -> None:
    """A place holding another policy answers 404, keeps it, and wakes no table."""
    world.attach("default", "namespace", ["prod", "sales"])
    world.changes.calls.clear()

    response = world.detach("gold", "namespace", ["prod", "sales"])

    assert response.status_code == 404
    assert "is not attached to namespace" in response.json()["detail"]
    assert len(_listed(world, "default")) == 1
    assert world.changes.calls == []


def test_deleting_a_policy_still_attached_is_409_naming_the_places(world: PolicyWebWorld) -> None:
    """DELETE of a policy a place holds answers 409 listing the places, and the policy stays."""
    world.attach("gold", "catalog", ["prod"])
    world.attach("gold", "table", ["prod", "sales", "eu", "orders"])

    response = world.client.delete("/v1/maintenance-policies/gold")

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "maintenance policy gold is still attached to catalog:prod, table:prod.sales.eu.orders"
    )
    assert world.client.get("/v1/maintenance-policies/gold").status_code == 200


@pytest.mark.parametrize(
    ("method", "body"),
    [
        ("GET", None),
        ("PUT", {"target": {"type": "namespace", "path": ["prod", "sales"]}}),
        ("DELETE", {"target": {"type": "namespace", "path": ["prod", "sales"]}}),
    ],
)
def test_mappings_routes_are_gone(world: PolicyWebWorld, method: str, body: dict[str, object] | None) -> None:
    """An old client still calling ``/mappings`` is told so, and nothing is attached or detached."""
    world.attach("gold", "catalog", ["prod"])

    response = world.client.request(method, "/v1/maintenance-policies/gold/mappings", json=body)

    assert response.status_code == 404
    assert len(_listed(world)) == 1


def test_detach_by_attachment_id_is_gone(world: PolicyWebWorld) -> None:
    """The old ``DELETE .../attachments/{id}`` route no longer exists, and the place keeps the policy."""
    world.attach("gold", "catalog", ["prod"])

    response = world.client.delete("/v1/maintenance-policies/gold/attachments/pa-01m7sd16b1ef2vww335cwcg9k8")

    assert response.status_code in {404, 405}
    assert len(_listed(world)) == 1
