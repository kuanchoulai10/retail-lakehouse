"""Test the discovery policy routes over the real services on in-memory fakes."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context.table_maintenance.application.domain.model.catalog import Catalog
from context.table_maintenance.application.domain.model.shared import CatalogId, TableDiscoveryPolicyId
from tests.context.table_maintenance.adapter.inbound.web.discovery_policy_web_world import (
    DiscoveryPolicyWebWorld,
    discovery_policy_body,
    discovery_rule,
)
from tests.context.table_maintenance.id_shape import IdShape

DP_ID = IdShape(TableDiscoveryPolicyId)
NOW = datetime(2026, 11, 1, tzinfo=UTC)


@pytest.fixture
def world() -> DiscoveryPolicyWebWorld:
    """Provide a client over no discovery policy."""
    return DiscoveryPolicyWebWorld()


def _attach(world: DiscoveryPolicyWebWorld, policy_id: str, catalog: str) -> None:
    place = Catalog.register(CatalogId(catalog), NOW)
    place.attach_discovery_policy(TableDiscoveryPolicyId(policy_id), NOW)
    world.catalogs.create(place)


def test_post_then_get_round_trips_the_body(world: DiscoveryPolicyWebWorld) -> None:
    """POST answers 201 at version 1 with the description and the rules in the order sent."""
    first = discovery_rule("*")
    second = discovery_rule("*_tmp", action="exclude")

    created = world.create("sales-tables", first, second, description="Sales")

    assert DP_ID.fullmatch(created["id"])
    assert set(created) == {"id", "name", "version", "created_at", "updated_at", "description", "rules"}
    assert {k: created[k] for k in ("name", "version", "description", "rules")} == {
        "name": "sales-tables",
        "version": 1,
        "description": "Sales",
        "rules": [first, second],
    }
    assert created["created_at"] == created["updated_at"]
    assert world.client.get("/v1/discovery-policies/sales-tables").json() == created


def test_post_accepts_exclude_rules_only(world: DiscoveryPolicyWebWorld) -> None:
    """A policy may hold one exclude rule and nothing else."""
    response = world.client.post(
        "/v1/discovery-policies",
        json={"name": "nothing", "rules": [{"action": "exclude", "table_name_pattern": "*"}]},
    )
    assert response.status_code == 201, response.text
    assert response.json()["rules"] == [{"action": "exclude", "table_name_pattern": "*"}]


def test_post_defaults_the_description(world: DiscoveryPolicyWebWorld) -> None:
    """A create body may leave the description out."""
    response = world.client.post("/v1/discovery-policies", json={"name": "bare", "rules": [discovery_rule()]})
    assert response.status_code == 201, response.text
    assert response.json()["description"] == ""


def test_post_with_no_rules_is_422(world: DiscoveryPolicyWebWorld) -> None:
    """A policy needs at least one rule, and nothing is stored."""
    response = world.client.post("/v1/discovery-policies", json={"name": "empty", "rules": []})
    assert response.status_code == 422
    assert world.client.get("/v1/discovery-policies/empty").status_code == 404


def test_post_of_the_old_shape_is_422(world: DiscoveryPolicyWebWorld) -> None:
    """A body with a no-match outcome, or a rule with an outcome and conditions, is refused."""
    old_outcome = {"name": "old", "no_match_outcome": "unmanage", "rules": [discovery_rule()]}
    assert world.client.post("/v1/discovery-policies", json=old_outcome).status_code == 422
    old_rule = {
        "name": "old",
        "rules": [
            {"outcome": "manage", "conditions": [{"attribute": "table_name", "operator": "glob", "values": ["*"]}]}
        ],
    }
    assert world.client.post("/v1/discovery-policies", json=old_rule).status_code == 422
    assert world.client.get("/v1/discovery-policies/old").status_code == 404


def test_post_refuses_an_unknown_field_or_action(world: DiscoveryPolicyWebWorld) -> None:
    """Request bodies forbid extra keys at every level and take only the known actions."""
    extra = {"name": "x", **discovery_policy_body(discovery_rule(id="dr-00000000000000000000000001"))}
    assert world.client.post("/v1/discovery-policies", json=extra).status_code == 422
    bad_action = {"name": "x", **discovery_policy_body(discovery_rule(action="manage"))}
    assert world.client.post("/v1/discovery-policies", json=bad_action).status_code == 422
    assert world.client.get("/v1/discovery-policies/x").status_code == 404


def test_post_with_an_empty_pattern_is_422(world: DiscoveryPolicyWebWorld) -> None:
    """A table name pattern must not be empty."""
    response = world.client.post("/v1/discovery-policies", json={"name": "x", "rules": [discovery_rule("")]})
    assert response.status_code == 422
    assert "must not be empty" in response.json()["detail"]


def test_post_with_a_taken_name_is_409(world: DiscoveryPolicyWebWorld) -> None:
    """Names are unique among discovery policies."""
    world.create("mine")
    response = world.client.post("/v1/discovery-policies", json={"name": "mine", **discovery_policy_body()})
    assert response.status_code == 409


def test_put_replaces_the_rules_and_bumps_the_version(world: DiscoveryPolicyWebWorld) -> None:
    """PUT from the current version answers the next version with the rules sent."""
    world.create("mine", discovery_rule())

    response = world.update("mine", 1, discovery_rule("*"), discovery_rule("*_tmp", action="exclude"))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["version"] == 2
    assert body["rules"] == [discovery_rule("*"), discovery_rule("*_tmp", action="exclude")]
    assert world.client.get("/v1/discovery-policies/mine").json() == body


def test_put_with_no_rules_is_422(world: DiscoveryPolicyWebWorld) -> None:
    """A revision needs at least one rule, and nothing is saved."""
    world.create("mine")
    response = world.client.put("/v1/discovery-policies/mine", json={"version": 1, "description": "", "rules": []})
    assert response.status_code == 422
    assert world.client.get("/v1/discovery-policies/mine").json()["version"] == 1


def test_put_from_a_stale_version_is_409(world: DiscoveryPolicyWebWorld) -> None:
    """A PUT from a version that is no longer current is a conflict and saves nothing."""
    world.create("mine", discovery_rule())
    assert world.update("mine", 1, discovery_rule()).status_code == 200
    response = world.update("mine", 1, discovery_rule("stale_*"))
    assert response.status_code == 409
    assert response.json() == {"detail": "discovery policy mine is at version 2, not 1"}
    assert world.client.get("/v1/discovery-policies/mine/versions/3").status_code == 404


def test_put_unknown_policy_is_404(world: DiscoveryPolicyWebWorld) -> None:
    """A PUT to a name no policy has is not found."""
    assert world.update("missing", 1, discovery_rule()).status_code == 404


def test_get_unknown_policy_is_404(world: DiscoveryPolicyWebWorld) -> None:
    """A name no policy has is not found."""
    response = world.client.get("/v1/discovery-policies/missing")
    assert response.status_code == 404
    assert response.json() == {"detail": "discovery policy missing not found"}


def test_there_is_no_default_discovery_policy(world: DiscoveryPolicyWebWorld) -> None:
    """No discovery policy named ``default`` exists until someone creates one."""
    assert world.client.get("/v1/discovery-policies/default").status_code == 404
    assert world.client.get("/v1/discovery-policies").json() == {"policies": []}


def test_get_version_answers_the_rules_it_was_written_with(world: DiscoveryPolicyWebWorld) -> None:
    """Version 1 keeps its description and rules after an update; the body has no ``updated_at``."""
    created = world.create("mine", discovery_rule(), description="first")
    world.update("mine", 1, discovery_rule("x_*"), description="second")

    body = world.client.get("/v1/discovery-policies/mine/versions/1").json()

    assert body == {k: v for k, v in created.items() if k != "updated_at"}


def test_get_version_0_is_404(world: DiscoveryPolicyWebWorld) -> None:
    """No policy has a version 0."""
    world.create("mine")
    response = world.client.get("/v1/discovery-policies/mine/versions/0")
    assert response.status_code == 404
    assert response.json() == {"detail": "discovery policy mine has no version 0"}


def test_list_orders_by_name_with_attachment_counts(world: DiscoveryPolicyWebWorld) -> None:
    """The policies come by name, each with its attachment count."""
    zeta = world.create("zeta", discovery_rule())
    world.create("alpha")
    _attach(world, zeta["id"], "prod")

    body = world.client.get("/v1/discovery-policies").json()

    assert [(p["name"], p["attachment_count"]) for p in body["policies"]] == [("alpha", 0), ("zeta", 1)]
    assert {k: v for k, v in body["policies"][1].items() if k != "attachment_count"} == zeta


def test_delete_answers_204_then_the_policy_is_gone(world: DiscoveryPolicyWebWorld) -> None:
    """A detached policy is deleted with its versions."""
    world.create("mine")
    response = world.client.delete("/v1/discovery-policies/mine")
    assert response.status_code == 204
    assert world.client.get("/v1/discovery-policies/mine").status_code == 404
    assert world.client.get("/v1/discovery-policies/mine/versions/1").status_code == 404


def test_delete_of_an_attached_policy_is_409(world: DiscoveryPolicyWebWorld) -> None:
    """An attached policy is not deleted; the answer names each place it is attached to."""
    mine = world.create("mine")
    _attach(world, mine["id"], "prod")
    response = world.client.delete("/v1/discovery-policies/mine")
    assert response.status_code == 409
    assert response.json()["detail"] == "discovery policy mine is still attached to catalog:prod"
    assert world.client.get("/v1/discovery-policies/mine").status_code == 200
