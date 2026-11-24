"""A catalog the platform's credential cannot read: attaching is 403, and a scan records ``cannot_access``.

The catalog is made unreadable by taking the content grants from its ``catalog_admin`` role, never the
role itself; ``CATALOG_MANAGE_ACCESS`` stays, so each scenario grants them back as its first undo.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from e2e.support import OwnedNames, wait_until

if TYPE_CHECKING:
    import httpx

    from e2e.support import CleanupStack, OwnedCatalog, PlatformApi, PolarisClient

pytestmark = pytest.mark.full

POLICIES = "/v1/discovery-policies"
NEVER = {"outcome": "manage", "conditions": [{"attribute": "table_name", "operator": "glob", "values": ["never_*"]}]}
SCAN_SECONDS = 90


def _delete_if_present(api: httpx.Client, path: str) -> None:
    reply = api.delete(path)
    assert reply.status_code in (204, 404), f"DELETE {path} answered {reply.status_code}: {reply.text}"


def _grants(polaris: PolarisClient, catalog: str) -> set[str]:
    reply = polaris.management("GET", f"/catalogs/{catalog}/catalog-roles/catalog_admin/grants")
    assert reply.is_success, f"grants of {catalog} answered {reply.status_code}: {reply.text}"
    return {grant["privilege"] for grant in reply.json()["grants"]}


def _make_unreadable(owned: OwnedCatalog, polaris: PolarisClient, cleanup: CleanupStack) -> None:
    assert "CATALOG_MANAGE_ACCESS" in _grants(polaris, owned.name)
    owned.revoke_reads(polaris)
    cleanup.push(f"grant reads back on {owned.name}", lambda: owned.restore_reads(polaris))
    assert "CATALOG_MANAGE_ACCESS" in _grants(polaris, owned.name)


def _policy(platform: PlatformApi, api: httpx.Client, cleanup: CleanupStack, name: str) -> dict:
    created = platform.call(
        "POST", POLICIES, {"name": name, "description": "e2e", "no_match_outcome": "unmanage", "rules": [NEVER]}
    )
    cleanup.push(f"delete {name}", lambda: _delete_if_present(api, f"{POLICIES}/{name}"))
    return created


def _scanned(platform: PlatformApi, catalog: str) -> dict | None:
    return next(
        (found for found in platform.get("/v1/scanned-catalogs")["catalogs"] if found["catalog"] == catalog), None
    )


def _rescan(platform: PlatformApi, name: str, description: str) -> None:
    """Save the attached policy again: a save rescans every catalog it is attached in."""
    version = platform.get(f"{POLICIES}/{name}")["version"]
    body = {"version": version, "description": description, "no_match_outcome": "unmanage", "rules": [NEVER]}
    platform.call("PUT", f"{POLICIES}/{name}", body)


def test_attaching_in_an_unreadable_catalog_is_forbidden(
    api: httpx.Client,
    platform: PlatformApi,
    polaris: PolarisClient,
    owned_catalog: OwnedCatalog,
    suffix: str,
    cleanup: CleanupStack,
):
    """The attach and the effective policies of its namespace answer 403 with the reason, and nothing is stored."""
    namespace = OwnedNames.namespace(suffix, "unreadable")
    owned_catalog.iceberg.create_namespace((namespace,))
    cleanup.push(f"drop {namespace}", lambda: owned_catalog.iceberg.drop_namespace((namespace,)))
    name = OwnedNames.discovery_policy(suffix, "unreadable")
    _policy(platform, api, cleanup, name)
    _make_unreadable(owned_catalog, polaris, cleanup)

    refused = api.put(
        f"{POLICIES}/{name}/attachments",
        json={"target": {"type": "namespace", "path": [owned_catalog.name, namespace]}},
    )
    if refused.is_success:
        attachment = refused.json()["id"]
        cleanup.push(f"detach {name}", lambda: _delete_if_present(api, f"{POLICIES}/{name}/attachments/{attachment}"))
    assert refused.status_code == 403 and refused.json()["detail"], refused.text
    assert platform.get(f"{POLICIES}/{name}/attachments")["attachments"] == []
    effective = api.get("/v1/effective-policies", params={"catalog": owned_catalog.name, "namespace": namespace})
    assert effective.status_code == 403 and effective.json()["detail"], effective.text


def test_a_catalog_that_turns_unreadable_is_recorded_cannot_access(
    api: httpx.Client,
    platform: PlatformApi,
    polaris: PolarisClient,
    owned_catalog: OwnedCatalog,
    suffix: str,
    cleanup: CleanupStack,
):
    """A rescan of the unreadable catalog shows ``cannot_access``; once readable again the failure clears."""
    catalog = owned_catalog.name
    name = OwnedNames.discovery_policy(suffix, "access")
    _policy(platform, api, cleanup, name)
    attachment = platform.attach("discovery-policies", name, {"type": "catalog", "path": [catalog]})
    cleanup.push(f"detach {name}", lambda: _delete_if_present(api, f"{POLICIES}/{name}/attachments/{attachment}"))

    def readable() -> dict:
        found = _scanned(platform, catalog)
        if found is None or found["failure"] is not None or found["last_discovered_at"] is None:
            raise AssertionError(found)
        return found

    first = wait_until(readable, timeout=SCAN_SECONDS, interval=3, what=f"{catalog} scanned")
    _make_unreadable(owned_catalog, polaris, cleanup)
    _rescan(platform, name, "e2e: rescan while unreadable")

    def failed() -> dict:
        found = _scanned(platform, catalog)
        if found is None or found["failure"] is None:
            raise AssertionError(found)
        return found

    unreadable = wait_until(failed, timeout=SCAN_SECONDS, interval=3, what=f"{catalog} recorded cannot_access")
    failure = unreadable["failure"]
    assert (failure["reason"], bool(failure["detail"]), bool(failure["failed_at"])) == ("cannot_access", True, True)
    assert unreadable["last_discovered_at"] == first["last_discovered_at"]

    owned_catalog.restore_reads(polaris)
    _rescan(platform, name, "e2e: rescan once readable")
    again = wait_until(
        lambda: found if (found := readable())["last_discovered_at"] != first["last_discovered_at"] else None,
        timeout=SCAN_SECONDS,
        interval=3,
        what=f"{catalog} scanned again",
    )
    assert again["failure"] is None
