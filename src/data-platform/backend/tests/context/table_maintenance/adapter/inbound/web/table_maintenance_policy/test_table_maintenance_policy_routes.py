"""Test the maintenance policy routes over the real services on in-memory fakes."""

from __future__ import annotations

import pytest

from tests.context.table_maintenance.adapter.inbound.web.policy_web_world import PolicyWebWorld, policy_body


@pytest.fixture
def world() -> PolicyWebWorld:
    """Provide a client over the default policy and one managed table."""
    return PolicyWebWorld()


def test_create_then_get_answers_the_content_flat_with_server_fields(world: PolicyWebWorld) -> None:
    """POST creates version 1; GET answers name, version, timestamps and the content's fields."""
    created = world.create("gold", description="Gold tier", dry_run=True)
    assert created["version"] == 1
    body = world.client.get("/v1/maintenance-policies/gold").json()
    assert body == created
    assert body["name"] == "gold"
    assert body["description"] == "Gold tier"
    assert body["dry_run"] is True
    assert body["reconcile_interval_seconds"] == 3600
    assert body["operations"]["rewrite_data_files"]["scope"] == {"unit": "partition"}
    assert body["operations"]["rewrite_data_files"]["trigger_policy"] == {
        "cooldown_seconds": 3600,
        "conditions": {"reducible_files": {"at_least": 5}},
    }
    assert body["operations"]["remove_orphan_files"]["execution_policy"] == {"older_than_seconds": 259200}


def test_create_accepts_a_missing_condition_as_not_checked(world: PolicyWebWorld) -> None:
    """A condition left out of the body is not checked."""
    content = policy_body()
    content["operations"]["rewrite_data_files"]["trigger_policy"]["conditions"] = {}
    response = world.client.post("/v1/maintenance-policies", json={"name": "lazy", **content})
    assert response.status_code == 201, response.text
    conditions = response.json()["operations"]["rewrite_data_files"]["trigger_policy"]["conditions"]
    assert conditions.get("reducible_files") is None


def test_list_policies_carries_attachment_counts(world: PolicyWebWorld) -> None:
    """GET lists every policy with how many targets it is attached to."""
    world.create("gold")
    assert world.attach("gold", "catalog", ["prod"]).status_code == 200
    body = world.client.get("/v1/maintenance-policies").json()
    assert {p["name"]: p["attachment_count"] for p in body["policies"]} == {"default": 0, "gold": 1}


def test_create_duplicate_name_is_409(world: PolicyWebWorld) -> None:
    """A taken name answers 409."""
    world.create("gold")
    response = world.client.post("/v1/maintenance-policies", json={"name": "gold", **policy_body()})
    assert response.status_code == 409


def _with_orphan_older_than(seconds: int) -> dict[str, object]:
    content = policy_body()
    content["operations"]["remove_orphan_files"]["execution_policy"]["older_than_seconds"] = seconds
    return content


def _with_reconcile_interval(seconds: int) -> dict[str, object]:
    return {**policy_body(), "reconcile_interval_seconds": seconds}


def _with_cooldown(seconds: int) -> dict[str, object]:
    content = policy_body()
    content["operations"]["expire_snapshots"]["trigger_policy"]["cooldown_seconds"] = seconds
    return content


@pytest.mark.parametrize(
    "body",
    [
        {"name": "bad name", **policy_body()},
        {"name": "gold", **_with_orphan_older_than(3600)},
        {"name": "gold", **policy_body(unknown=1)},
        {"name": "gold", **_with_reconcile_interval(0)},
        {"name": "gold", **_with_reconcile_interval(-60)},
        {"name": "gold", **_with_cooldown(-1)},
    ],
)
def test_create_broken_invariant_is_422(world: PolicyWebWorld, body: dict[str, object]) -> None:
    """A bad name, a broken invariant or an unknown field answers 422."""
    response = world.client.post("/v1/maintenance-policies", json=body)
    assert response.status_code == 422


def test_put_with_current_version_increments_it(world: PolicyWebWorld) -> None:
    """PUT with the version read replaces the content and answers the next version."""
    world.create("gold")
    response = world.client.put("/v1/maintenance-policies/gold", json={"version": 1, **policy_body(dry_run=True)})
    assert response.status_code == 200, response.text
    assert (response.json()["version"], response.json()["dry_run"]) == (2, True)


def test_stale_put_is_409_and_changes_nothing(world: PolicyWebWorld) -> None:
    """PUT with a version the policy has moved past answers 409 and leaves the policy as it was."""
    world.create("gold")
    assert world.client.put("/v1/maintenance-policies/gold", json={"version": 1, **policy_body()}).status_code == 200
    response = world.client.put("/v1/maintenance-policies/gold", json={"version": 1, **policy_body(dry_run=True)})
    assert response.status_code == 409
    current = world.client.get("/v1/maintenance-policies/gold").json()
    assert (current["version"], current["dry_run"]) == (2, False)


def test_put_missing_policy_is_404(world: PolicyWebWorld) -> None:
    """PUT on an unknown policy answers 404."""
    response = world.client.put("/v1/maintenance-policies/nope", json={"version": 1, **policy_body()})
    assert response.status_code == 404


def test_get_old_version_after_update(world: PolicyWebWorld) -> None:
    """An older version stays readable, unchanged, after the policy moved on."""
    world.create("gold", description="first")
    world.client.put("/v1/maintenance-policies/gold", json={"version": 1, **policy_body(description="second")})
    old = world.client.get("/v1/maintenance-policies/gold/versions/1")
    assert old.status_code == 200
    assert (old.json()["version"], old.json()["description"]) == (1, "first")
    assert world.client.get("/v1/maintenance-policies/gold/versions/2").json()["description"] == "second"
    assert world.client.get("/v1/maintenance-policies/gold/versions/3").status_code == 404


def test_put_wakes_the_managed_tables_it_applies_to(world: PolicyWebWorld) -> None:
    """Updating the default policy tells the table that falls back to it."""
    world.client.put("/v1/maintenance-policies/default", json={"version": 1, **policy_body()})
    assert [(c.table_uuid, c.change) for c in world.changes.calls] == [("u-1", "policy_changed")]


def test_delete_unattached_policy_is_204(world: PolicyWebWorld) -> None:
    """DELETE removes a policy nothing is attached to."""
    world.create("gold")
    assert world.client.delete("/v1/maintenance-policies/gold").status_code == 204
    assert world.client.get("/v1/maintenance-policies/gold").status_code == 404


def test_delete_attached_policy_is_409(world: PolicyWebWorld) -> None:
    """DELETE of a policy still attached answers 409 and keeps it."""
    world.create("gold")
    world.attach("gold", "namespace", ["prod", "sales"])
    assert world.client.delete("/v1/maintenance-policies/gold").status_code == 409
    assert world.client.get("/v1/maintenance-policies/gold").status_code == 200


def test_delete_default_is_409(world: PolicyWebWorld) -> None:
    """The default policy cannot be deleted."""
    assert world.client.delete("/v1/maintenance-policies/default").status_code == 409


def test_delete_missing_is_404(world: PolicyWebWorld) -> None:
    """DELETE of an unknown policy answers 404."""
    assert world.client.delete("/v1/maintenance-policies/nope").status_code == 404
