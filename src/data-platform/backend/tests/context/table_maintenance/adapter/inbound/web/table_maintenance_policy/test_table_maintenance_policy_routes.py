"""Test the maintenance policy routes over the real services on in-memory fakes."""

from __future__ import annotations

import pytest

from shared_kernel import prefixed_id_pattern
from tests.context.table_maintenance.adapter.inbound.web.policy_web_world import PolicyWebWorld, policy_body
from tests.context.table_maintenance.fakes.default_content_json import DEFAULT_CONTENT_JSON

MP_ID = prefixed_id_pattern("mp")
DEFAULT_POLICY_ID = "mp-00000000000000000000000000"
OPERATIONS = ("rewrite_data_files", "rewrite_manifests", "expire_snapshots", "remove_orphan_files")


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
    assert body["on"] == {"schedule": {"every_seconds": 3600}, "catalog_commit": {"debounce_seconds": 300}}
    assert body["rewrite_data_files"] == {
        "target": {"reducible_files": {"at_most": 5}, "per": "partition"},
        "options": {"min_input_files": 2, "partial_progress_enabled": True},
    }
    assert body["remove_orphan_files"] == {"target": {"older_than_seconds": 259200}, "options": None}


def test_create_accepts_the_new_shape(world: PolicyWebWorld) -> None:
    """The documented content creates a policy and comes back unchanged beside the server's fields."""
    response = world.client.post("/v1/maintenance-policies", json={"name": "gold", **DEFAULT_CONTENT_JSON})
    assert response.status_code == 201, response.text
    body = response.json()
    assert {key: body[key] for key in DEFAULT_CONTENT_JSON} == DEFAULT_CONTENT_JSON
    assert "operations" not in body
    assert "priority" not in body
    assert "reconcile_interval_seconds" not in body


def test_create_defaults_dry_run_and_the_debounce(world: PolicyWebWorld) -> None:
    """``dry_run`` defaults to false and a catalog commit trigger to a five-minute debounce."""
    content = {key: value for key, value in DEFAULT_CONTENT_JSON.items() if key != "dry_run"}
    content["on"] = {"schedule": {"every_seconds": 600}, "catalog_commit": {}}
    response = world.client.post("/v1/maintenance-policies", json={"name": "gold", **content})
    assert response.status_code == 201, response.text
    assert response.json()["dry_run"] is False
    assert response.json()["on"] == {"schedule": {"every_seconds": 600}, "catalog_commit": {"debounce_seconds": 300}}


def test_create_accepts_a_policy_without_blocks(world: PolicyWebWorld) -> None:
    """A policy may hold no operation block: it is checked and does nothing."""
    body = {"name": "idle", "description": "nothing", "on": {"schedule": {"every_seconds": 3600}}}
    response = world.client.post("/v1/maintenance-policies", json=body)
    assert response.status_code == 201, response.text
    created = response.json()
    assert [created[op] for op in OPERATIONS] == [None] * 4
    assert created["on"] == {"schedule": {"every_seconds": 3600}, "catalog_commit": None}


def test_create_refuses_an_option_that_repeats_the_target(world: PolicyWebWorld) -> None:
    """``retain_last`` is the target's ``min_snapshots_to_keep``, so it is no option."""
    content = policy_body()
    content["expire_snapshots"] = {"target": {"min_snapshots_to_keep": 3}, "options": {"retain_last": 3}}
    response = world.client.post("/v1/maintenance-policies", json={"name": "gold", **content})
    assert response.status_code == 422
    assert [(e["type"], e["loc"]) for e in response.json()["detail"]] == [
        ("extra_forbidden", ["body", "expire_snapshots", "options", "retain_last"])
    ]
    assert world.client.get("/v1/maintenance-policies/gold").status_code == 404


def test_update_refuses_an_option_that_repeats_the_target(world: PolicyWebWorld) -> None:
    """The target file size is the table's, so PUT with it as an option is 422 and the version stays."""
    world.create("gold")
    content = policy_body()
    content["rewrite_data_files"]["options"] = {"target_file_size_bytes": 1024}
    response = world.client.put("/v1/maintenance-policies/gold", json={"version": 1, **content})
    assert response.status_code == 422
    assert [(e["type"], e["loc"]) for e in response.json()["detail"]] == [
        ("extra_forbidden", ["body", "rewrite_data_files", "options", "target_file_size_bytes"])
    ]
    assert world.client.get("/v1/maintenance-policies/gold").json()["version"] == 1


@pytest.mark.parametrize(
    "removed",
    [{"priority": "P2"}, {"reconcile_interval_seconds": 3600}, {"operations": {}}],
)
def test_create_refuses_the_old_fields(world: PolicyWebWorld, removed: dict[str, object]) -> None:
    """The fields of the shape before targets are unknown."""
    response = world.client.post("/v1/maintenance-policies", json={"name": "gold", **policy_body(**removed)})
    assert response.status_code == 422


def test_update_without_a_block_removes_it(world: PolicyWebWorld) -> None:
    """PUT replaces the whole content: a block left out is gone and reads back as null."""
    world.create("gold")
    content = policy_body()
    del content["remove_orphan_files"]
    response = world.client.put("/v1/maintenance-policies/gold", json={"version": 1, **content})
    assert response.status_code == 200, response.text
    current = world.client.get("/v1/maintenance-policies/gold").json()
    assert current["remove_orphan_files"] is None
    assert current["expire_snapshots"] == DEFAULT_CONTENT_JSON["expire_snapshots"]
    assert world.client.get("/v1/maintenance-policies/gold/versions/1").json()["remove_orphan_files"] is not None


def test_responses_leave_unset_options_out(world: PolicyWebWorld) -> None:
    """An option not set is not written; an options object not given is null."""
    content = policy_body()
    content["remove_orphan_files"] = {"target": {"older_than_seconds": 86400}, "options": {"max_concurrent_deletes": 4}}
    content["rewrite_manifests"] = {"target": {"small_manifests": {"at_most": 2}}}
    created = world.client.post("/v1/maintenance-policies", json={"name": "gold", **content}).json()
    assert created["remove_orphan_files"]["options"] == {"max_concurrent_deletes": 4}
    assert created["rewrite_manifests"]["options"] is None
    listed = next(p for p in world.client.get("/v1/maintenance-policies").json()["policies"] if p["name"] == "gold")
    assert listed["remove_orphan_files"]["options"] == {"max_concurrent_deletes": 4}


def test_policy_routes_still_use_names(world: PolicyWebWorld) -> None:
    """Every policy route is addressed by name; each answer adds the policy's ``mp-`` id beside the name."""
    created = world.create("gold")
    policy_id = created["id"]
    assert MP_ID.match(policy_id)
    assert world.client.get("/v1/maintenance-policies/gold").json()["id"] == policy_id
    put = world.client.put("/v1/maintenance-policies/gold", json={"version": 1, **policy_body()})
    assert put.json()["id"] == policy_id
    assert world.client.get("/v1/maintenance-policies/gold/versions/1").json()["id"] == policy_id
    listed = world.client.get("/v1/maintenance-policies").json()["policies"]
    assert {p["name"]: p["id"] for p in listed} == {"default": DEFAULT_POLICY_ID, "gold": policy_id}
    assert world.client.get(f"/v1/maintenance-policies/{policy_id}").status_code == 422
    assert world.client.delete("/v1/maintenance-policies/gold").status_code == 204


def test_every_policy_answer_says_whether_it_is_the_default(world: PolicyWebWorld) -> None:
    """Each answer carries ``is_default``, true only for the platform default, so no client compares names."""
    created = world.create("gold")
    assert created["is_default"] is False
    assert world.client.get("/v1/maintenance-policies/default").json()["is_default"] is True
    assert world.client.get("/v1/maintenance-policies/gold").json()["is_default"] is False
    put = world.client.put("/v1/maintenance-policies/gold", json={"version": 1, **policy_body()})
    assert put.json()["is_default"] is False
    assert world.client.get("/v1/maintenance-policies/default/versions/1").json()["is_default"] is True
    listed = world.client.get("/v1/maintenance-policies").json()["policies"]
    assert {p["name"]: p["is_default"] for p in listed} == {"default": True, "gold": False}


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
    return policy_body(remove_orphan_files={"target": {"older_than_seconds": seconds}})


def _with_schedule(seconds: int) -> dict[str, object]:
    return policy_body(on={"schedule": {"every_seconds": seconds}})


@pytest.mark.parametrize(
    "body",
    [
        {"name": "bad name", **policy_body()},
        {"name": "gold", **_with_orphan_older_than(3600)},
        {"name": "gold", **policy_body(unknown=1)},
        {"name": "gold", **_with_schedule(59)},
        {"name": "gold", **_with_schedule(604801)},
        {
            "name": "gold",
            **policy_body(on={"schedule": {"every_seconds": 3600}, "catalog_commit": {"debounce_seconds": -1}}),
        },
        {"name": "gold", **policy_body(on={})},
        {"name": "gold", **policy_body(rewrite_data_files={"target": {"reducible_files": {"at_most": -1}}})},
        {
            "name": "gold",
            **policy_body(
                rewrite_data_files={"target": {"reducible_files": {"at_most": 5}}, "options": {"strategy": "zorder"}}
            ),
        },
    ],
)
def test_create_broken_invariant_is_422(world: PolicyWebWorld, body: dict[str, object]) -> None:
    """A bad name, a broken invariant or an unknown field answers 422."""
    response = world.client.post("/v1/maintenance-policies", json=body)
    assert response.status_code == 422


def test_broken_invariant_detail_names_the_dotted_field(world: PolicyWebWorld) -> None:
    """A broken invariant deep in the content answers 422 with one line naming the dotted field."""
    response = world.client.post("/v1/maintenance-policies", json={"name": "gold", **_with_orphan_older_than(3600)})
    assert (response.status_code, response.json()) == (
        422,
        {"detail": "remove_orphan_files.target.older_than_seconds: must be at least 1 day"},
    )


def test_create_with_a_name_shaped_like_an_id_is_422(world: PolicyWebWorld) -> None:
    """A policy named like an ``mp-`` id answers 422 with a message that says why."""
    response = world.client.post(
        "/v1/maintenance-policies", json={"name": "mp-01kaa4zc9qf3v8d2m6xk0w7b1n", **policy_body()}
    )
    assert response.status_code == 422
    assert "must not look like a prefixed id" in response.json()["detail"]


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
