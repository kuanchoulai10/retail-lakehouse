"""A catalog the platform's credential cannot read: attaching is 403, and a scan records ``cannot_access``.

The catalog is made unreadable by taking the content grants from its ``catalog_admin`` role, never the
role itself; ``CATALOG_MANAGE_ACCESS`` stays, so each scenario grants them back as its first undo. A
round of the one discovery schedule scans every catalog on its own, so an unreadable one does not stop
the others; the round is triggered by hand, and only the module's own catalogs are looked at.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyarrow as pa
import pytest
from temporalio.client import WorkflowExecutionStatus

from e2e.support import (
    OwnedCatalog,
    OwnedNames,
    drop_table,
    latest_run,
    load_iceberg,
    trigger_schedule,
    wait_until,
    wait_until_unmanaged,
)

if TYPE_CHECKING:
    import httpx
    from pyarrow import fs
    from temporalio.client import Client

    from e2e.support import CleanupStack, E2eSettings, PlatformApi, PolarisClient, TemporalSession

pytestmark = pytest.mark.full

POLICIES = "/v1/discovery-policies"
NEVER = {"action": "include", "table_name_pattern": "never_*"}
INCLUDE_ALL = {"action": "include", "table_name_pattern": "*"}
SCAN_SECONDS = 90
ROUND_SECONDS = 180
ROWS = pa.schema([pa.field("id", pa.int64())])


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


def _policy(platform: PlatformApi, api: httpx.Client, cleanup: CleanupStack, name: str, rule: dict = NEVER) -> dict:
    created = platform.call("POST", POLICIES, {"name": name, "description": "e2e", "rules": [rule]})
    cleanup.push(f"delete {name}", lambda: _delete_if_present(api, f"{POLICIES}/{name}"))
    return created


def _scanned(platform: PlatformApi, catalog: str) -> dict | None:
    return next(
        (found for found in platform.get("/v1/scanned-catalogs")["catalogs"] if found["catalog"] == catalog), None
    )


def _attach_to_catalog(platform: PlatformApi, cleanup: CleanupStack, name: str, catalog: str) -> None:
    target = {"type": "catalog", "path": [catalog]}
    platform.attach("discovery", name, target)
    cleanup.push(f"detach {name}", lambda: platform.detach("discovery", name, target, missing_ok=True))


def _readable(platform: PlatformApi, catalog: str) -> dict:
    """Return the catalog's scan record once it has a completed scan and no current failure; raise until then."""
    found = _scanned(platform, catalog)
    if found is None or found["failure"] is not None or found["last_discovered_at"] is None:
        raise AssertionError(found)
    return found


def _scanned_after(platform: PlatformApi, catalog: str, before: dict | None) -> dict | None:
    """Return the catalog's scan record once it holds a completed scan other than ``before``'s; None until then.

    ``before`` is None for a catalog not listed before: any completed scan is newer.
    """
    found = _readable(platform, catalog)
    if before is not None and found["last_discovered_at"] == before["last_discovered_at"]:
        return None
    return found


def _scan_finished(temporal: TemporalSession[Client], catalog: str) -> bool | None:
    """Return True once the catalog's latest scan is closed; None while one runs (or none ever ran)."""
    run = latest_run(temporal, f"table-discovery:catalog={catalog}")
    return True if run is not None and run[1] != WorkflowExecutionStatus.RUNNING else None


def _rescan(platform: PlatformApi, name: str, description: str) -> None:
    """Save the attached policy again: a save rescans every catalog it is attached in."""
    version = platform.get(f"{POLICIES}/{name}")["version"]
    body = {"version": version, "description": description, "rules": [NEVER]}
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

    target = {"type": "namespace", "path": [owned_catalog.name, namespace]}
    refused = api.put(f"{POLICIES}/{name}/attachments", json={"target": target})
    if refused.is_success:
        cleanup.push(f"detach {name}", lambda: platform.detach("discovery", name, target, missing_ok=True))
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
    _attach_to_catalog(platform, cleanup, name, catalog)

    first = wait_until(
        lambda: _readable(platform, catalog), timeout=SCAN_SECONDS, interval=3, what=f"{catalog} scanned"
    )
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
        lambda: _scanned_after(platform, catalog, first),
        timeout=SCAN_SECONDS,
        interval=3,
        what=f"{catalog} scanned again",
    )
    assert again["failure"] is None


def test_an_unreadable_catalog_does_not_stop_the_round(
    api: httpx.Client,
    platform: PlatformApi,
    polaris: PolarisClient,
    temporal: TemporalSession[Client],
    s3: fs.S3FileSystem,
    settings: E2eSettings,
    owned_catalog: OwnedCatalog,
    suffix: str,
    cleanup: CleanupStack,
):
    """A round started by the schedule records ``cannot_access`` for A and still scans B, whose table is managed.

    Both catalogs hold a discovery policy, so the round scans both. Nothing but the round scans either
    after A is made unreadable: A's failure and B's newer scan are the round's. A dry-run maintenance
    policy keeps B's managed table from running any job.
    """
    unreadable = owned_catalog
    readable = OwnedCatalog.create(
        platform=platform,
        polaris=polaris,
        s3=s3,
        cleanup=cleanup,
        platform_catalog=settings.catalog,
        name=OwnedNames.catalog(suffix, "unreadable_round_readable"),
        load_iceberg=lambda warehouse: load_iceberg(settings, warehouse),
    )
    namespace = OwnedNames.namespace(suffix, "round")
    readable.iceberg.create_namespace((namespace,))
    cleanup.push(f"drop {namespace}", lambda: readable.iceberg.drop_namespace((namespace,)))
    readable.iceberg.create_table((namespace, "b1"), ROWS)
    cleanup.push(f"drop {namespace}.b1", lambda: drop_table(readable.iceberg, s3, (namespace, "b1")))
    dry = OwnedNames.maintenance_policy(suffix, "round")
    platform.create_maintenance_policy(dry, "e2e: dry run", lambda body: {**body, "dry_run": True})
    cleanup.push(f"delete {dry}", lambda: _delete_if_present(api, f"/v1/maintenance-policies/{dry}"))
    on_namespace = {"type": "namespace", "path": [readable.name, namespace]}
    platform.attach("maintenance", dry, on_namespace)
    cleanup.push(f"detach {dry}", lambda: platform.detach("maintenance", dry, on_namespace, missing_ok=True))
    cleanup.push(
        f"wait until {namespace}.b1 is unmanaged",
        lambda: wait_until_unmanaged(platform, temporal, (readable.name, namespace, "b1")),
    )

    never = OwnedNames.discovery_policy(suffix, "round_never")
    everything = OwnedNames.discovery_policy(suffix, "round_all")
    earlier = {c: found for c in (unreadable.name, readable.name) if (found := _scanned(platform, c))}
    _policy(platform, api, cleanup, never)
    _attach_to_catalog(platform, cleanup, never, unreadable.name)
    _policy(platform, api, cleanup, everything, INCLUDE_ALL)
    _attach_to_catalog(platform, cleanup, everything, readable.name)
    first_a, first_b = (
        wait_until(
            lambda c=c: _scanned_after(platform, c, earlier.get(c)),
            timeout=SCAN_SECONDS,
            interval=3,
            what=f"{c} scanned, as the attach asks",
        )
        for c in (unreadable.name, readable.name)
    )
    for catalog in (unreadable.name, readable.name):
        wait_until(
            lambda catalog=catalog: _scan_finished(temporal, catalog),
            timeout=SCAN_SECONDS,
            interval=3,
            what=f"the scan of {catalog} the attach asked for finished, so only the round scans it next",
        )

    _make_unreadable(unreadable, polaris, cleanup)
    trigger_schedule(temporal, "table-discovery")

    def failed() -> dict:
        found = _scanned(platform, unreadable.name)
        if found is None or found["failure"] is None:
            raise AssertionError(found)
        return found

    failure = wait_until(failed, timeout=ROUND_SECONDS, interval=3, what=f"{unreadable.name} recorded cannot_access")
    assert failure["failure"]["reason"] == "cannot_access", failure
    assert failure["last_discovered_at"] == first_a["last_discovered_at"]
    wait_until(
        lambda: _scanned_after(platform, readable.name, first_b),
        timeout=ROUND_SECONDS,
        interval=3,
        what=f"{readable.name} scanned again by the same round",
    )

    def managed() -> dict:
        found = platform.table(readable.name, namespace, "b1")
        if found is None or found["status"] != "managed":
            raise AssertionError(found)
        return found

    table = wait_until(managed, timeout=ROUND_SECONDS, interval=3, what=f"{readable.name}.{namespace}.b1 managed")
    assert table["decided_by"]["rule_position"] == 1, table
