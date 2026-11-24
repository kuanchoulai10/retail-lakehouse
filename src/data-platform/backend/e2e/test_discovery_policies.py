"""Discovery policies answer through the API: the default stays fixed, attaching needs a real place, saving versions.

All of it is API answers; what a scan then does with a policy is in the discovery lifecycle scenario.
Each scenario attaches only in a catalog of the module's own, so ``iceberg``'s scans are not changed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from e2e.support import OwnedNames, assert_prefixed_ids, schedule_exists, wait_until

if TYPE_CHECKING:
    import httpx
    from temporalio.client import Client

    from e2e.support import CleanupStack, OwnedCatalog, PlatformApi, TemporalSession

pytestmark = pytest.mark.critical

POLICIES = "/v1/discovery-policies"
MANAGE_ORDERS = {
    "outcome": "manage",
    "conditions": [{"attribute": "table_name", "operator": "glob", "values": ["orders_*"]}],
}
UNMANAGE_TMP = {
    "outcome": "unmanage",
    "conditions": [{"attribute": "table_name", "operator": "glob", "values": ["tmp_*"]}],
}
MANAGE_SALES = {
    "outcome": "manage",
    "conditions": [{"attribute": "namespace", "operator": "glob", "values": ["sales*"]}],
}


def _delete_if_present(api: httpx.Client, path: str) -> None:
    reply = api.delete(path)
    assert reply.status_code in (204, 404), f"DELETE {path} answered {reply.status_code}: {reply.text}"


def _create(platform: PlatformApi, api: httpx.Client, cleanup: CleanupStack, name: str, rules: list[dict]) -> dict:
    created = platform.call(
        "POST", POLICIES, {"name": name, "description": "e2e", "no_match_outcome": "unmanage", "rules": rules}
    )
    cleanup.push(f"delete {name}", lambda: _delete_if_present(api, f"{POLICIES}/{name}"))
    return created


def _attach(api: httpx.Client, cleanup: CleanupStack, name: str, target: dict) -> httpx.Response:
    reply = api.put(f"{POLICIES}/{name}/attachments", json={"target": target})
    if reply.is_success:
        path = f"{POLICIES}/{name}/attachments/{reply.json()['id']}"
        cleanup.push(f"detach {name} from {target['path']}", lambda: _delete_if_present(api, path))
    return reply


def _attachment_ids(platform: PlatformApi, name: str) -> list[str]:
    return [attachment["id"] for attachment in platform.get(f"{POLICIES}/{name}/attachments")["attachments"]]


def test_the_default_discovery_policy_manages_nothing_and_cannot_change(api: httpx.Client, platform: PlatformApi):
    """The seeded default has no rules and leaves every table unmanaged; saving or deleting it is refused."""
    default = platform.get(f"{POLICIES}/default")
    assert (default["is_default"], default["rules"], default["no_match_outcome"]) == (True, [], "unmanage")
    assert_prefixed_ids({"dp": [default["id"]]})
    unchanged = {key: default[key] for key in ("version", "description", "no_match_outcome", "rules")}
    saved = api.put(f"{POLICIES}/default", json=unchanged)
    assert saved.status_code == 409, saved.text
    deleted = api.delete(f"{POLICIES}/default")
    assert deleted.status_code == 409, deleted.text
    assert platform.get(f"{POLICIES}/default") == default


def test_a_policy_attaches_to_an_empty_namespace_and_never_to_a_missing_place(
    api: httpx.Client,
    platform: PlatformApi,
    temporal: TemporalSession[Client],
    owned_catalog: OwnedCatalog,
    suffix: str,
    cleanup: CleanupStack,
):
    """An empty namespace may hold an attachment; a missing namespace or catalog is 404 and stores nothing."""
    name = OwnedNames.discovery_policy(suffix, "attach")
    _create(platform, api, cleanup, name, [MANAGE_ORDERS])
    namespace = OwnedNames.namespace(suffix, "attach")
    platform.call("POST", f"/v1/catalogs/{owned_catalog.name}/namespaces", {"namespace": [namespace]})
    cleanup.push(
        f"drop {namespace}",
        lambda: _delete_if_present(api, f"/v1/catalogs/{owned_catalog.name}/namespaces/{namespace}"),
    )

    attached = _attach(api, cleanup, name, {"type": "namespace", "path": [owned_catalog.name, namespace]})
    assert attached.status_code == 200, attached.text
    assert_prefixed_ids({"da": [attached.json()["id"]]})
    assert _attachment_ids(platform, name) == [attached.json()["id"]]
    owned_schedule = f"table-discovery:catalog={owned_catalog.name}"
    wait_until(
        lambda: schedule_exists(temporal, owned_schedule) or None,
        timeout=60,
        interval=2,
        what=f"{owned_schedule} created",
    )

    missing_catalog = OwnedNames.catalog(suffix, "missing")
    for target in (
        {"type": "namespace", "path": [owned_catalog.name, "no_such_ns"]},
        {"type": "catalog", "path": [missing_catalog]},
    ):
        refused = _attach(api, cleanup, name, target)
        assert refused.status_code == 404, f"{target}: {refused.status_code} {refused.text}"
        assert refused.json()["detail"], refused.text
    assert _attachment_ids(platform, name) == [attached.json()["id"]]
    assert not schedule_exists(temporal, f"table-discovery:catalog={missing_catalog}")


def test_saving_a_policy_makes_a_version_and_keeps_its_rule_ids(
    api: httpx.Client, platform: PlatformApi, owned_catalog: OwnedCatalog, suffix: str, cleanup: CleanupStack
):
    """A save makes version 2 and keeps version 1 readable; a stale save and deleting an attached policy are 409."""
    name = OwnedNames.discovery_policy(suffix, "versions")
    first = _create(platform, api, cleanup, name, [MANAGE_ORDERS, UNMANAGE_TMP])
    orders, tmp = first["rules"]
    assert first["version"] == 1
    assert_prefixed_ids({"dp": [first["id"]], "dr": [orders["id"], tmp["id"]]})

    update: dict[str, Any] = {
        "version": 1,
        "description": "e2e, saved",
        "no_match_outcome": "unmanage",
        "rules": [tmp, orders, MANAGE_SALES],
    }
    second = platform.call("PUT", f"{POLICIES}/{name}", update)
    assert second["version"] == 2
    kept, added = [rule["id"] for rule in second["rules"][:2]], second["rules"][2]["id"]
    assert kept == [tmp["id"], orders["id"]]
    assert_prefixed_ids({"dr": [added]})
    assert added not in kept

    original = platform.get(f"{POLICIES}/{name}/versions/1")
    assert (original["version"], original["description"], original["rules"]) == (1, "e2e", first["rules"])
    stale = api.put(f"{POLICIES}/{name}", json=update)
    assert stale.status_code == 409, stale.text
    assert platform.get(f"{POLICIES}/{name}")["version"] == 2

    attached = _attach(api, cleanup, name, {"type": "catalog", "path": [owned_catalog.name]})
    assert attached.status_code == 200, attached.text
    refused = api.delete(f"{POLICIES}/{name}")
    assert refused.status_code == 409, refused.text
    platform.call("DELETE", f"{POLICIES}/{name}/attachments/{attached.json()['id']}")
    deleted = api.delete(f"{POLICIES}/{name}")
    assert deleted.status_code == 204, deleted.text
    assert api.get(f"{POLICIES}/{name}").status_code == 404
