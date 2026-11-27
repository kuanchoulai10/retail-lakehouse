"""Test the discovery policy attachment routes over the real services on in-memory fakes."""

from __future__ import annotations

import logging

import pytest

from context.table_maintenance.application.domain.model.shared import (
    TableDiscoveryPolicyAttachmentId,
    TableMaintenancePolicyAttachmentId,
)
from tests.context.table_maintenance.adapter.inbound.web.discovery_policy_web_world import (
    NOW,
    DiscoveryPolicyWebWorld,
    discovery_rule,
)
from tests.context.table_maintenance.id_shape import IdShape

DA_ID = IdShape(TableDiscoveryPolicyAttachmentId)


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


def test_put_attachment_answers_the_attachment(client: DiscoveryPolicyWebWorld) -> None:
    """PUT attachments answers 200 with the new ``da-`` id, the target and the policy."""
    response = client.attach("sales", "table", ["iceberg", "sales", "orders"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert DA_ID.fullmatch(body.pop("id"))
    assert body == {
        "target": {"type": "table", "path": ["iceberg", "sales", "orders"], "table_uuid": "u-1"},
        "policy_id": _policy_id(client, "sales"),
        "policy_name": "sales",
        "attached_at": NOW.isoformat().replace("+00:00", "Z"),
    }


def test_put_attachment_twice_keeps_the_id(client: DiscoveryPolicyWebWorld) -> None:
    """Attaching another policy to the same target replaces it and answers the same id."""
    first = client.attach("sales", "catalog", ["iceberg"]).json()

    second = client.attach("others", "catalog", ["iceberg"]).json()

    assert second["id"] == first["id"]
    assert second["policy_name"] == "others"
    assert client.client.get("/v1/discovery-policies/sales/attachments").json() == {"attachments": []}


def test_put_attachment_in_a_refused_catalog_is_403(client: DiscoveryPolicyWebWorld) -> None:
    """A catalog the credential cannot read answers 403 naming it, and nothing is stored."""
    client.catalog.deny("iceberg")

    response = client.attach("sales", "namespace", ["iceberg", "sales"])

    assert response.status_code == 403
    assert response.json()["detail"] == "the platform's catalog credential cannot read catalog iceberg"
    assert client.attachments.list_all() == []


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
    """A target or a policy that does not exist answers 404, and nothing is stored."""
    assert client.attach(name, type_, path).status_code == 404
    assert client.attachments.list_all() == []


def test_put_attachment_with_an_extra_field_is_422(client: DiscoveryPolicyWebWorld) -> None:
    """The request refuses fields it does not know."""
    response = client.client.put(
        "/v1/discovery-policies/sales/attachments",
        json={"target": {"type": "catalog", "path": ["iceberg"], "table_uuid": "u-1"}},
    )

    assert response.status_code == 422


def test_get_attachments_marks_orphans(client: DiscoveryPolicyWebWorld) -> None:
    """GET attachments lists the policy's attachments with their ids; a target that is gone is orphaned."""
    catalog = client.attach("sales", "catalog", ["iceberg"]).json()
    namespace = client.attach("sales", "namespace", ["iceberg", "sales"]).json()
    client.catalog.drop_namespace("iceberg", "sales")

    response = client.client.get("/v1/discovery-policies/sales/attachments")

    assert response.status_code == 200
    listed = {a["id"]: a for a in response.json()["attachments"]}
    assert listed == {
        catalog["id"]: {**catalog, "orphaned": False},
        namespace["id"]: {**namespace, "orphaned": True},
    }


def test_get_attachments_in_a_refused_catalog_stays_200_and_not_orphaned(client: DiscoveryPolicyWebWorld) -> None:
    """A catalog the credential cannot read does not fail the list, and its attachments are not orphaned."""
    client.attach("sales", "namespace", ["iceberg", "sales"])
    client.catalog.deny("iceberg")

    response = client.client.get("/v1/discovery-policies/sales/attachments")

    assert response.status_code == 200
    assert [a["orphaned"] for a in response.json()["attachments"]] == [False]


def test_get_attachments_of_an_unknown_policy_is_404(client: DiscoveryPolicyWebWorld) -> None:
    """Listing the attachments of a policy that does not exist answers 404."""
    assert client.client.get("/v1/discovery-policies/ghost/attachments").status_code == 404


def test_delete_attachment_answers_204_and_frees_the_policy(client: DiscoveryPolicyWebWorld) -> None:
    """DELETE by id answers 204 with no body; the policy, no longer attached, can then be deleted."""
    attached = client.attach("sales", "catalog", ["iceberg"]).json()
    assert client.client.delete("/v1/discovery-policies/sales").status_code == 409

    response = client.detach("sales", attached["id"])

    assert (response.status_code, response.content) == (204, b"")
    assert client.attachments.list_all() == []
    assert client.client.delete("/v1/discovery-policies/sales").status_code == 204


def test_delete_attachment_of_a_dropped_catalog_is_204(client: DiscoveryPolicyWebWorld) -> None:
    """An attachment whose catalog is gone is detached by id."""
    attached = client.attach("sales", "catalog", ["iceberg"]).json()
    client.catalog.drop_catalog("iceberg")

    assert client.detach("sales", attached["id"]).status_code == 204


def test_delete_attachment_answers_204_when_temporal_fails(
    client: DiscoveryPolicyWebWorld, caplog: pytest.LogCaptureFixture
) -> None:
    """A detach whose final scan and schedule sync both fail is still stored, answers 204 and logs."""
    attached = client.attach("sales", "catalog", ["iceberg"]).json()
    client.requests.failing.add("iceberg")
    client.schedules.failing = True

    with caplog.at_level(logging.WARNING):
        response = client.detach("sales", attached["id"])

    assert response.status_code == 204
    assert client.attachments.list_all() == []
    assert "could not start discovery in catalog iceberg" in caplog.text
    assert "could not sync the discovery schedules" in caplog.text


@pytest.mark.parametrize("attachment_id", ["x", TableMaintenancePolicyAttachmentId.new().value])
def test_delete_with_a_malformed_id_is_422(client: DiscoveryPolicyWebWorld, attachment_id: str) -> None:
    """An id that is not a ``da-`` id, a maintenance ``pa-`` id among them, answers 422."""
    response = client.detach("sales", attachment_id)

    assert response.status_code == 422
    assert "da-" in response.json()["detail"]


def test_delete_of_another_policys_attachment_is_404(client: DiscoveryPolicyWebWorld) -> None:
    """An attachment of another policy answers 404 and stays."""
    attached = client.attach("others", "catalog", ["iceberg"]).json()

    response = client.detach("sales", attached["id"])

    assert response.status_code == 404
    assert response.json()["detail"] == f"policy sales has no attachment {attached['id']}"
    assert len(client.attachments.list_all()) == 1
