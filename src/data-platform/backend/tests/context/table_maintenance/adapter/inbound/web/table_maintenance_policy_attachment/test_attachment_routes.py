"""Test the policy mapping and applicable policy routes over the real services on in-memory fakes."""

from __future__ import annotations

import pytest

from tests.context.table_maintenance.adapter.inbound.web.policy_web_world import PolicyWebWorld


@pytest.fixture
def world() -> PolicyWebWorld:
    """Provide a client over the default policy, a gold policy and one managed table prod.sales.eu.orders."""
    world = PolicyWebWorld()
    world.create("gold")
    return world


def test_attach_answers_the_mapping_and_wakes_the_table(world: PolicyWebWorld) -> None:
    """PUT mappings attaches the policy to the target and tells the table whose policy changed."""
    response = world.attach("gold", "namespace", ["prod", "sales"])
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["target"] == {"type": "namespace", "path": ["prod", "sales"], "table_uuid": None}
    assert (body["policy_id"], body["policy_name"]) == (_gold_id(world), "gold")
    assert [(c.table_uuid, c.change) for c in world.changes.calls] == [("u-1", "policy_changed")]


def _gold_id(world: PolicyWebWorld) -> str:
    return world.client.get("/v1/maintenance-policies/gold").json()["id"]


def test_attach_to_a_table_resolves_its_uuid(world: PolicyWebWorld) -> None:
    """A table target's path is catalog, namespace levels and table; the mapping carries its uuid."""
    response = world.attach("gold", "table", ["prod", "sales", "eu", "orders"])
    assert response.status_code == 200, response.text
    assert response.json()["target"]["table_uuid"] == "u-1"


@pytest.mark.parametrize(
    ("type_", "path"),
    [
        ("table", ["prod", "sales", "eu", "ghost"]),
        ("namespace", ["prod", "missing"]),
        ("catalog", ["nope"]),
    ],
)
def test_attach_to_a_target_missing_from_the_catalog_is_404(world: PolicyWebWorld, type_: str, path: list[str]) -> None:
    """A table, namespace or catalog missing from the catalog answers 404 and nothing is attached."""
    assert world.attach("gold", type_, path).status_code == 404
    assert world.attachments.list_all() == []


def test_attach_unknown_policy_is_404(world: PolicyWebWorld) -> None:
    """Attaching a policy that does not exist answers 404."""
    assert world.attach("nope", "catalog", ["prod"]).status_code == 404


def test_attach_with_a_bad_target_type_is_422(world: PolicyWebWorld) -> None:
    """An unknown target type answers 422."""
    assert world.attach("gold", "table-like", ["prod", "sales", "orders"]).status_code == 422


def test_list_mappings_marks_orphans(world: PolicyWebWorld) -> None:
    """GET mappings lists the policy's attachments; one whose target left the catalog is orphaned."""
    world.attach("gold", "catalog", ["prod"])
    world.attach("gold", "namespace", ["prod", "sales"])
    world.catalog.drop_table("prod", "sales.eu", "orders")
    body = world.client.get("/v1/maintenance-policies/gold/mappings").json()
    assert sorted((m["target"]["type"], m["orphaned"]) for m in body["mappings"]) == [
        ("catalog", True),
        ("namespace", True),
    ]
    assert {(m["policy_id"], m["policy_name"]) for m in body["mappings"]} == {(_gold_id(world), "gold")}


def test_list_mappings_of_an_unknown_policy_is_404(world: PolicyWebWorld) -> None:
    """GET mappings of a policy that does not exist answers 404, like GET and DELETE of the same name."""
    assert world.client.get("/v1/maintenance-policies/nope/mappings").status_code == 404


def test_list_mappings_keeps_live_targets_not_orphaned(world: PolicyWebWorld) -> None:
    """A target still in the catalog is not orphaned."""
    world.attach("gold", "table", ["prod", "sales", "eu", "orders"])
    body = world.client.get("/v1/maintenance-policies/gold/mappings").json()
    assert [(m["target"]["table_uuid"], m["orphaned"]) for m in body["mappings"]] == [("u-1", False)]


def test_detach_removes_the_mapping_and_wakes_the_table(world: PolicyWebWorld) -> None:
    """DELETE mappings detaches the policy from the target and tells the table."""
    world.attach("gold", "namespace", ["prod", "sales"])
    world.changes.calls.clear()
    response = world.client.request(
        "DELETE",
        "/v1/maintenance-policies/gold/mappings",
        json={"target": {"type": "namespace", "path": ["prod", "sales"]}},
    )
    assert response.status_code == 204, response.text
    assert world.attachments.list_all() == []
    assert [c.table_uuid for c in world.changes.calls] == ["u-1"]


def test_detach_of_another_policys_mapping_is_404(world: PolicyWebWorld) -> None:
    """DELETE through a policy that is not the one attached there answers 404 and keeps the mapping."""
    world.attach("default", "namespace", ["prod", "sales"])
    response = world.client.request(
        "DELETE",
        "/v1/maintenance-policies/gold/mappings",
        json={"target": {"type": "namespace", "path": ["prod", "sales"]}},
    )
    assert response.status_code == 404
    assert len(world.attachments.list_all()) == 1


def test_detach_an_orphaned_table_mapping_by_uuid(world: PolicyWebWorld) -> None:
    """A table gone from the catalog is detached with the uuid its mapping carries."""
    world.attach("gold", "table", ["prod", "sales", "eu", "orders"])
    world.catalog.drop_table("prod", "sales.eu", "orders")
    target = {"type": "table", "path": ["prod", "sales", "eu", "orders"], "table_uuid": "u-1"}
    response = world.client.request("DELETE", "/v1/maintenance-policies/gold/mappings", json={"target": target})
    assert response.status_code == 204, response.text


def test_table_applicable_policy_names_where_it_came_from(world: PolicyWebWorld) -> None:
    """GET /tables/{uuid}/applicable-policy answers the policy, its version and the target it is inherited from."""
    world.attach("gold", "namespace", ["prod", "sales"])
    body = world.client.get("/v1/tables/u-1/applicable-policy").json()
    assert (body["id"], body["name"], body["version"]) == (_gold_id(world), "gold", 1)
    assert body["target"] == {"type": "namespace", "path": ["prod", "sales"], "table_uuid": None}
    assert body["operations"]["rewrite_data_files"]["enabled"] is True


def test_table_applicable_policy_falls_back_to_default(world: PolicyWebWorld) -> None:
    """With nothing attached the default applies and the target is null."""
    body = world.client.get("/v1/tables/u-1/applicable-policy").json()
    assert (body["id"], body["name"], body["target"]) == ("mp-00000000000000000000000000", "default", None)


def test_unknown_table_applicable_policy_is_404(world: PolicyWebWorld) -> None:
    """A table uuid table maintenance does not know answers 404."""
    assert world.client.get("/v1/tables/u-404/applicable-policy").status_code == 404


def test_applicable_policy_for_a_namespace_and_a_catalog(world: PolicyWebWorld) -> None:
    """GET /applicable-policy takes a catalog and an optional dotted namespace."""
    world.attach("gold", "catalog", ["prod"])
    world.attach("default", "namespace", ["prod", "sales"])
    namespace = world.client.get("/v1/applicable-policy", params={"catalog": "prod", "namespace": "sales.eu"}).json()
    assert (namespace["name"], namespace["target"]["path"]) == ("default", ["prod", "sales"])
    catalog = world.client.get("/v1/applicable-policy", params={"catalog": "prod"}).json()
    assert (catalog["name"], catalog["target"]["type"]) == ("gold", "catalog")


def test_applicable_policy_for_a_table_table_maintenance_has_no_record_of(world: PolicyWebWorld) -> None:
    """GET /applicable-policy with a table resolves it through the catalog; its own attachment applies."""
    world.catalog.add_table("prod", "sales.eu", "returns", "u-2")
    params = {"catalog": "prod", "namespace": "sales.eu", "table": "returns"}
    world.attach("default", "namespace", ["prod", "sales"])
    inherited = world.client.get("/v1/applicable-policy", params=params).json()
    assert (inherited["name"], inherited["target"]["type"]) == ("default", "namespace")
    assert world.attach("gold", "table", ["prod", "sales", "eu", "returns"]).status_code == 200
    own = world.client.get("/v1/applicable-policy", params=params).json()
    assert (own["name"], own["target"]) == (
        "gold",
        {"type": "table", "path": ["prod", "sales", "eu", "returns"], "table_uuid": "u-2"},
    )


def test_applicable_policy_for_a_table_missing_from_the_catalog_is_404(world: PolicyWebWorld) -> None:
    """A table the catalog does not hold answers 404."""
    params = {"catalog": "prod", "namespace": "sales.eu", "table": "ghost"}
    assert world.client.get("/v1/applicable-policy", params=params).status_code == 404
