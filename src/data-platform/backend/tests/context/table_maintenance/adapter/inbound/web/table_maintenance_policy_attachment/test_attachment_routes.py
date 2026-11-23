"""Test the maintenance policy attachment routes over the real services on in-memory fakes."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.shared import (
    TableDiscoveryPolicyAttachmentId,
    TableMaintenancePolicyAttachmentId,
)
from tests.context.table_maintenance.adapter.inbound.web.policy_web_world import NOW, PolicyWebWorld
from tests.context.table_maintenance.id_shape import IdShape

PA_ID = IdShape(TableMaintenancePolicyAttachmentId)


@pytest.fixture
def world() -> PolicyWebWorld:
    """Provide a client over the default policy, a gold policy and one managed table prod.sales.eu.orders."""
    world = PolicyWebWorld()
    world.create("gold")
    return world


def _gold_id(world: PolicyWebWorld) -> str:
    return world.client.get("/v1/maintenance-policies/gold").json()["id"]


def test_put_attachment_answers_the_attachment(world: PolicyWebWorld) -> None:
    """PUT attachments answers 200 with the new ``pa-`` id, the target and the policy."""
    response = world.attach("gold", "namespace", ["prod", "sales"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert PA_ID.fullmatch(body.pop("id"))
    assert body == {
        "target": {"type": "namespace", "path": ["prod", "sales"], "table_uuid": None},
        "policy_id": _gold_id(world),
        "policy_name": "gold",
        "attached_at": NOW.isoformat().replace("+00:00", "Z"),
    }


def test_put_attachment_wakes_the_table(world: PolicyWebWorld) -> None:
    """Attaching tells the table whose applicable policy changed."""
    world.attach("gold", "namespace", ["prod", "sales"])

    assert [(c.table_uuid, c.change) for c in world.changes.calls] == [("u-1", "policy_changed")]


def test_put_attachment_twice_keeps_the_id(world: PolicyWebWorld) -> None:
    """Attaching another policy to the same target replaces it and answers the same id."""
    first = world.attach("gold", "catalog", ["prod"]).json()

    second = world.attach("default", "catalog", ["prod"]).json()

    assert second["id"] == first["id"]
    assert second["policy_name"] == "default"
    assert world.client.get("/v1/maintenance-policies/gold/attachments").json() == {"attachments": []}


def test_put_attachment_to_a_table_resolves_its_uuid(world: PolicyWebWorld) -> None:
    """A table target's path is catalog, namespace levels and table; the attachment carries its uuid."""
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
def test_put_attachment_to_a_target_missing_from_the_catalog_is_404(
    world: PolicyWebWorld, type_: str, path: list[str]
) -> None:
    """A table, namespace or catalog missing from the catalog answers 404 and nothing is attached."""
    assert world.attach("gold", type_, path).status_code == 404
    assert world.attachments.list_all() == []


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
    assert world.attachments.list_all() == []


def test_get_attachments_marks_orphans(world: PolicyWebWorld) -> None:
    """GET attachments lists the policy's attachments with their ids; a target that is gone is orphaned."""
    catalog = world.attach("gold", "catalog", ["prod"]).json()
    namespace = world.attach("gold", "namespace", ["prod", "sales"]).json()
    gone = world.attach("gold", "namespace", ["prod", "sales", "eu"]).json()
    world.catalog.drop_table("prod", "sales.eu", "orders")
    world.catalog.drop_namespace("prod", "sales.eu")

    response = world.client.get("/v1/maintenance-policies/gold/attachments")

    assert response.status_code == 200
    listed = {a["id"]: a for a in response.json()["attachments"]}
    assert listed == {
        catalog["id"]: {**catalog, "orphaned": False},
        namespace["id"]: {**namespace, "orphaned": False},
        gone["id"]: {**gone, "orphaned": True},
    }


def test_get_attachments_in_a_refused_catalog_stays_200_and_not_orphaned(world: PolicyWebWorld) -> None:
    """A catalog the credential cannot read does not fail the list; its attachment is not orphaned."""
    world.attach("gold", "catalog", ["prod"])
    world.catalog.deny("prod")
    response = world.client.get("/v1/maintenance-policies/gold/attachments")
    assert response.status_code == 200, response.text
    assert [a["orphaned"] for a in response.json()["attachments"]] == [False]


def test_get_attachments_of_an_unknown_policy_is_404(world: PolicyWebWorld) -> None:
    """GET attachments of a policy that does not exist answers 404, like GET and DELETE of the same name."""
    assert world.client.get("/v1/maintenance-policies/nope/attachments").status_code == 404


def test_get_attachments_keeps_live_targets_not_orphaned(world: PolicyWebWorld) -> None:
    """A target still in the catalog is not orphaned."""
    world.attach("gold", "table", ["prod", "sales", "eu", "orders"])
    body = world.client.get("/v1/maintenance-policies/gold/attachments").json()
    assert [(a["target"]["table_uuid"], a["orphaned"]) for a in body["attachments"]] == [("u-1", False)]


def test_delete_attachment_answers_204_and_wakes_the_table(world: PolicyWebWorld) -> None:
    """DELETE by id answers 204 with no body, removes the attachment and tells the table."""
    attached = world.attach("gold", "namespace", ["prod", "sales"]).json()
    world.changes.calls.clear()

    response = world.detach("gold", attached["id"])

    assert (response.status_code, response.content) == (204, b"")
    assert world.attachments.list_all() == []
    assert [(c.table_uuid, c.change) for c in world.changes.calls] == [("u-1", "policy_changed")]


def test_delete_an_orphaned_attachment_by_id(world: PolicyWebWorld) -> None:
    """An attachment whose table and catalog are gone is detached by id."""
    attached = world.attach("gold", "table", ["prod", "sales", "eu", "orders"]).json()
    world.catalog.drop_catalog("prod")

    assert world.detach("gold", attached["id"]).status_code == 204
    assert world.attachments.list_all() == []


def test_delete_attachment_in_a_refused_catalog_is_204(world: PolicyWebWorld) -> None:
    """Detaching does not read the catalog, so a catalog the credential cannot read does not stop it."""
    attached = world.attach("gold", "namespace", ["prod", "sales"]).json()
    world.catalog.deny("prod")

    assert world.detach("gold", attached["id"]).status_code == 204
    assert world.attachments.list_all() == []


@pytest.mark.parametrize("attachment_id", ["x", TableDiscoveryPolicyAttachmentId.new().value])
def test_delete_with_a_malformed_id_is_422(world: PolicyWebWorld, attachment_id: str) -> None:
    """An id that is not a ``pa-`` id, a discovery ``da-`` id among them, answers 422."""
    response = world.detach("gold", attachment_id)

    assert response.status_code == 422
    assert "pa-" in response.json()["detail"]


def test_delete_of_an_unknown_attachment_is_404(world: PolicyWebWorld) -> None:
    """A well-formed id that is not stored answers 404."""
    attached = world.attach("gold", "catalog", ["prod"]).json()
    assert world.detach("gold", attached["id"]).status_code == 204

    assert world.detach("gold", attached["id"]).status_code == 404


def test_delete_through_an_unknown_policy_is_404(world: PolicyWebWorld) -> None:
    """Detaching through a policy that does not exist answers 404 and keeps the attachment."""
    attached = world.attach("gold", "catalog", ["prod"]).json()

    assert world.detach("nope", attached["id"]).status_code == 404
    assert len(world.attachments.list_all()) == 1


def test_delete_of_another_policys_attachment_is_404(world: PolicyWebWorld) -> None:
    """An attachment of another policy answers 404, stays, and wakes no table."""
    attached = world.attach("default", "namespace", ["prod", "sales"]).json()
    world.changes.calls.clear()

    response = world.detach("gold", attached["id"])

    assert response.status_code == 404
    assert response.json()["detail"] == f"policy gold has no attachment {attached['id']}"
    assert len(world.attachments.list_all()) == 1
    assert world.changes.calls == []


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
    assert len(world.attachments.list_all()) == 1
