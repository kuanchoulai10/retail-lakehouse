"""Test the discovery policy routes over the real services on in-memory fakes."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context.table_maintenance.application.domain.model.shared import PolicyTarget, PolicyTargetType
from context.table_maintenance.application.domain.model.table_discovery_policy import TableDiscoveryPolicyId
from context.table_maintenance.application.domain.model.table_discovery_policy_attachment import (
    TableDiscoveryPolicyAttachment,
)
from shared_kernel import prefixed_id_pattern
from tests.context.table_maintenance.adapter.inbound.web.discovery_policy_web_world import (
    DiscoveryPolicyWebWorld,
    discovery_policy_body,
    discovery_rule,
)

DR_ID = prefixed_id_pattern("dr")
DP_ID = prefixed_id_pattern("dp")
DEFAULT_ID = "dp-00000000000000000000000000"
NOW = datetime(2026, 11, 1, tzinfo=UTC)


@pytest.fixture
def world() -> DiscoveryPolicyWebWorld:
    """Provide a client over the default discovery policy."""
    return DiscoveryPolicyWebWorld()


def _attach(world: DiscoveryPolicyWebWorld, policy_id: str, catalog: str) -> None:
    target = PolicyTarget(type=PolicyTargetType.CATALOG, path=(catalog,))
    world.attachments.create(TableDiscoveryPolicyAttachment.attach(target, TableDiscoveryPolicyId(policy_id), NOW))


def test_post_then_get_round_trips_the_body(world: DiscoveryPolicyWebWorld) -> None:
    """POST answers 201 at version 1 with the content flat; rule order and conditions come back unchanged."""
    first = {
        "outcome": "manage",
        "conditions": [
            {"attribute": "namespace", "operator": "glob", "values": ["sales", "sales.*"]},
            {"attribute": "table_name", "operator": "glob", "values": ["orders_*"]},
        ],
    }
    second = discovery_rule("tmp_*", outcome="unmanage")

    created = world.create("sales-tables", first, second, description="Sales", no_match_outcome="manage")

    assert DP_ID.fullmatch(created["id"])
    assert {k: created[k] for k in ("name", "is_default", "version", "description", "no_match_outcome")} == {
        "name": "sales-tables",
        "is_default": False,
        "version": 1,
        "description": "Sales",
        "no_match_outcome": "manage",
    }
    assert all(DR_ID.fullmatch(rule["id"]) for rule in created["rules"])
    assert [{k: v for k, v in rule.items() if k != "id"} for rule in created["rules"]] == [first, second]
    assert created["created_at"] == created["updated_at"]
    assert world.client.get("/v1/discovery-policies/sales-tables").json() == created


def test_post_defaults_the_description(world: DiscoveryPolicyWebWorld) -> None:
    """A create body may leave the description out."""
    response = world.client.post(
        "/v1/discovery-policies", json={"name": "bare", "no_match_outcome": "unmanage", "rules": []}
    )
    assert response.status_code == 201, response.text
    assert response.json()["description"] == ""


def test_post_refuses_an_unknown_field_or_outcome(world: DiscoveryPolicyWebWorld) -> None:
    """Request bodies forbid extra keys at every level and take only the known words."""
    extra = {"name": "x", **discovery_policy_body(discovery_rule(priority=1))}
    assert world.client.post("/v1/discovery-policies", json=extra).status_code == 422
    bad_outcome = {"name": "x", **discovery_policy_body(discovery_rule(outcome="ignore"))}
    assert world.client.post("/v1/discovery-policies", json=bad_outcome).status_code == 422
    assert world.client.get("/v1/discovery-policies/x").status_code == 404


def test_post_with_a_rule_id_is_422(world: DiscoveryPolicyWebWorld) -> None:
    """A create may name no rule id, however well-formed: the server issues every one, and nothing is stored."""
    body = {"name": "mine", **discovery_policy_body(discovery_rule(id="dr-00000000000000000000000001"))}
    response = world.client.post("/v1/discovery-policies", json=body)
    assert response.status_code == 422
    assert response.json() == {"detail": "unknown discovery rule id dr-00000000000000000000000001"}
    assert world.client.get("/v1/discovery-policies/mine").status_code == 404


def test_post_with_a_taken_name_is_409(world: DiscoveryPolicyWebWorld) -> None:
    """Names are unique among discovery policies."""
    world.create("mine")
    response = world.client.post("/v1/discovery-policies", json={"name": "mine", **discovery_policy_body()})
    assert response.status_code == 409


def test_put_keeps_sent_ids_and_bumps_the_version(world: DiscoveryPolicyWebWorld) -> None:
    """PUT from the current version answers the next version; a rule sent with its id keeps it."""
    created = world.create("mine", discovery_rule())
    kept = created["rules"][0]["id"]

    response = world.update("mine", 1, discovery_rule("new_*"), discovery_rule(id=kept))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["version"] == 2
    assert body["rules"][1]["id"] == kept
    assert body["rules"][0]["id"] != kept
    assert world.client.get("/v1/discovery-policies/mine").json() == body


def test_put_with_an_empty_rule_id_is_422(world: DiscoveryPolicyWebWorld) -> None:
    """``"id": ""`` is neither a ``dr-`` id nor absent, and nothing is saved."""
    world.create("mine", discovery_rule())
    response = world.update("mine", 1, discovery_rule(id=""))
    assert response.status_code == 422
    assert response.json() == {"detail": "a rule id is a dr- id or absent"}
    assert world.client.get("/v1/discovery-policies/mine").json()["version"] == 1


def test_put_with_two_table_name_conditions_is_422(world: DiscoveryPolicyWebWorld) -> None:
    """An attribute appears at most once per rule."""
    world.create("mine", discovery_rule())
    rule = {
        "outcome": "manage",
        "conditions": [
            {"attribute": "table_name", "operator": "glob", "values": ["a_*"]},
            {"attribute": "table_name", "operator": "glob", "values": ["b_*"]},
        ],
    }
    response = world.update("mine", 1, rule)
    assert response.status_code == 422
    assert "attribute table_name appears more than once" in response.json()["detail"]
    assert world.client.get("/v1/discovery-policies/mine").json()["version"] == 1


def test_put_with_another_policys_rule_id_is_422(world: DiscoveryPolicyWebWorld) -> None:
    """A rule id the policy does not hold is refused, and nothing is saved."""
    world.create("mine", discovery_rule())
    other = world.create("other", discovery_rule())
    response = world.update("mine", 1, discovery_rule(id=other["rules"][0]["id"]))
    assert response.status_code == 422
    assert response.json()["detail"].startswith("unknown discovery rule id dr-")
    assert world.client.get("/v1/discovery-policies/mine").json()["version"] == 1


def test_put_from_a_stale_version_is_409(world: DiscoveryPolicyWebWorld) -> None:
    """A PUT from a version that is no longer current is a conflict and saves nothing."""
    world.create("mine", discovery_rule())
    assert world.update("mine", 1, discovery_rule()).status_code == 200
    response = world.update("mine", 1, discovery_rule("stale_*"))
    assert response.status_code == 409
    assert response.json() == {"detail": "discovery policy mine is at version 2, not 1"}
    assert world.client.get("/v1/discovery-policies/mine/versions/3").status_code == 404


def test_put_default_is_409(world: DiscoveryPolicyWebWorld) -> None:
    """The default is fixed."""
    response = world.update("default", 1, discovery_rule())
    assert response.status_code == 409
    assert response.json() == {"detail": "the default discovery policy cannot be changed"}


def test_put_unknown_policy_is_404(world: DiscoveryPolicyWebWorld) -> None:
    """A PUT to a name no policy has is not found."""
    assert world.update("missing", 1, discovery_rule()).status_code == 404


def test_get_unknown_policy_is_404(world: DiscoveryPolicyWebWorld) -> None:
    """A name no policy has is not found."""
    response = world.client.get("/v1/discovery-policies/missing")
    assert response.status_code == 404
    assert response.json() == {"detail": "discovery policy missing not found"}


def test_get_default_answers_its_fixed_content(world: DiscoveryPolicyWebWorld) -> None:
    """The default has no rules and unmanages every table."""
    body = world.client.get("/v1/discovery-policies/default").json()
    assert (body["id"], body["is_default"], body["version"], body["rules"], body["no_match_outcome"]) == (
        DEFAULT_ID,
        True,
        1,
        [],
        "unmanage",
    )


def test_get_version_answers_the_content_it_was_written_with(world: DiscoveryPolicyWebWorld) -> None:
    """Version 1 keeps its content after an update; the body has no ``updated_at``."""
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


def test_list_puts_the_default_first_with_attachment_counts(world: DiscoveryPolicyWebWorld) -> None:
    """The default comes first, then the others by name, each with its attachment count."""
    zeta = world.create("zeta", discovery_rule())
    world.create("alpha")
    _attach(world, zeta["id"], "prod")

    body = world.client.get("/v1/discovery-policies").json()

    assert [(p["name"], p["attachment_count"]) for p in body["policies"]] == [
        ("default", 0),
        ("alpha", 0),
        ("zeta", 1),
    ]
    assert {k: v for k, v in body["policies"][2].items() if k != "attachment_count"} == zeta


def test_delete_answers_204_then_the_policy_is_gone(world: DiscoveryPolicyWebWorld) -> None:
    """A detached policy is deleted with its versions."""
    world.create("mine")
    response = world.client.delete("/v1/discovery-policies/mine")
    assert response.status_code == 204
    assert world.client.get("/v1/discovery-policies/mine").status_code == 404
    assert world.client.get("/v1/discovery-policies/mine/versions/1").status_code == 404


def test_delete_of_the_default_or_an_attached_policy_is_409(world: DiscoveryPolicyWebWorld) -> None:
    """The default is never deleted, and an attached policy is not deleted."""
    assert world.client.delete("/v1/discovery-policies/default").json() == {
        "detail": "the default discovery policy cannot be deleted"
    }
    mine = world.create("mine")
    _attach(world, mine["id"], "prod")
    response = world.client.delete("/v1/discovery-policies/mine")
    assert response.status_code == 409
    assert world.client.get("/v1/discovery-policies/mine").status_code == 200
