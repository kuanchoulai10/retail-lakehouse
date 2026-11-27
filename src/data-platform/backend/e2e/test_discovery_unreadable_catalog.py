"""A catalog the platform's credential cannot read: attaching is 403, and a scan records ``cannot_access``.

The catalog is made unreadable by taking the content grants from its ``catalog_admin`` role, never the
role itself; ``CATALOG_MANAGE_ACCESS`` stays, so each scenario grants them back as its first undo. A
round of the one discovery schedule scans every catalog on its own, so an unreadable one does not stop
the others; the round is triggered by hand, and only the module's own catalogs are looked at.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from temporalio.client import WorkflowExecutionStatus

from e2e.support import (
    OwnedCatalog,
    OwnedNames,
    latest_run,
    load_iceberg,
    scheduled_workflows,
    trigger_schedule,
    wait_until,
)

if TYPE_CHECKING:
    import httpx
    from pyarrow import fs
    from temporalio.client import Client

    from e2e.support import CleanupStack, E2eSettings, PlatformApi, PolarisClient, TemporalSession, WorkflowRun

pytestmark = pytest.mark.full

POLICIES = "/v1/discovery-policies"
NEVER = {"action": "include", "table_name_pattern": "never_*"}
INCLUDE_ALL = {"action": "include", "table_name_pattern": "*"}
SCAN_SECONDS = 90
ROUND_SECONDS = 180
SCHEDULE = "table-discovery"


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


def _scanned_after(platform: PlatformApi, catalog: str, before: dict) -> dict | None:
    """Return the catalog's scan record once it holds a completed scan newer than ``before``'s; None until then."""
    found = _readable(platform, catalog)
    return found if found["last_discovered_at"] != before["last_discovered_at"] else None


def _scan(catalog: str) -> str:
    return f"table-discovery:catalog={catalog}"


def _closed_scan_after(
    temporal: TemporalSession[Client], catalog: str, before: WorkflowRun | None
) -> WorkflowRun | None:
    """Return the catalog's latest scan run once it is another run than ``before`` and closed; None until then."""
    run = latest_run(temporal, _scan(catalog))
    if run is None or run.status == WorkflowExecutionStatus.RUNNING:
        return None
    return run if before is None or run.run_id != before.run_id else None


def _closed_scan_of_a_new_round(
    temporal: TemporalSession[Client], catalog: str, rounds_before: set[str]
) -> WorkflowRun | None:
    """Return the catalog's latest scan run once a round the schedule started since ``rounds_before`` started it.

    A round's scan names the round as its parent; a scan an attach or a catalog event asked for has none.
    """
    run = latest_run(temporal, _scan(catalog))
    if run is None or run.status == WorkflowExecutionStatus.RUNNING:
        return None
    rounds = set(scheduled_workflows(temporal, SCHEDULE)) - rounds_before
    return run if run.parent_id in rounds else None


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
    """A round the schedule starts records ``cannot_access`` for unreadable A and still completes B's scan.

    Both catalogs hold a discovery policy, so a round scans both. The starting points are read once the
    scans the attaches asked for have closed. After the trigger, each catalog's newest scan names a
    round started since as its parent, so it is the round's: A's records the failure and keeps its last
    scan time, B's completes with a newer one.
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
    never = OwnedNames.discovery_policy(suffix, "round_never")
    everything = OwnedNames.discovery_policy(suffix, "round_all")
    catalogs = (unreadable.name, readable.name)
    before_attach = {c: latest_run(temporal, _scan(c)) for c in catalogs}
    _policy(platform, api, cleanup, never)
    _attach_to_catalog(platform, cleanup, never, unreadable.name)
    _policy(platform, api, cleanup, everything, INCLUDE_ALL)
    _attach_to_catalog(platform, cleanup, everything, readable.name)
    for catalog in catalogs:
        wait_until(
            lambda catalog=catalog: _closed_scan_after(temporal, catalog, before_attach[catalog]),
            timeout=SCAN_SECONDS,
            interval=3,
            what=f"the scan of {catalog} the attach asked for closed, so only the round scans it next",
        )
    start = {c: _readable(platform, c) for c in catalogs}

    rounds_before = set(scheduled_workflows(temporal, SCHEDULE))
    _make_unreadable(unreadable, polaris, cleanup)
    trigger_schedule(temporal, SCHEDULE)
    by_round = {
        catalog: wait_until(
            lambda catalog=catalog: _closed_scan_of_a_new_round(temporal, catalog, rounds_before),
            timeout=ROUND_SECONDS,
            interval=3,
            what=f"a scan of {catalog} started by a round after the trigger, closed",
        )
        for catalog in catalogs
    }
    assert by_round[readable.name].status == WorkflowExecutionStatus.COMPLETED, by_round

    after = {c: _scanned(platform, c) for c in catalogs}
    failure = after[unreadable.name]
    assert failure is not None and failure["failure"] is not None, failure
    assert failure["failure"]["reason"] == "cannot_access", failure
    assert failure["last_discovered_at"] == start[unreadable.name]["last_discovered_at"], (start, failure)
    scanned = after[readable.name]
    assert scanned is not None and scanned["failure"] is None, scanned
    assert scanned["last_discovered_at"] != start[readable.name]["last_discovered_at"], (start, scanned)
