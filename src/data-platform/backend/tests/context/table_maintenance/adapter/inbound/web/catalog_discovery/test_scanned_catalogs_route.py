"""Test the scanned catalogs route over the real service on in-memory fakes."""

from __future__ import annotations

from datetime import timedelta

import pytest

from context.table_maintenance.application.domain.model.catalog_discovery import (
    CatalogDiscovery,
    CatalogScanFailure,
    CatalogScanFailureReason,
)
from tests.context.table_maintenance.adapter.inbound.web.discovery_policy_web_world import (
    NOW,
    DiscoveryPolicyWebWorld,
    discovery_rule,
)

LATER = NOW + timedelta(minutes=10)
REFUSED = "the platform's catalog credential cannot read catalog b"


def _iso(at):
    return at.isoformat().replace("+00:00", "Z")


@pytest.fixture
def client() -> DiscoveryPolicyWebWorld:
    """Provide a client over a managing ``sales`` and an excluding ``nothing`` policy, and catalogs a, b and c."""
    world = DiscoveryPolicyWebWorld()
    world.create("sales", discovery_rule())
    world.create("nothing", discovery_rule("*", action="exclude"))
    world.catalog.add_catalog("a")
    world.catalog.add_namespace("b", "ns")
    world.catalog.add_catalog("c")
    return world


def test_scanned_catalogs_list_every_catalog_a_policy_is_attached_in(client: DiscoveryPolicyWebWorld) -> None:
    """A catalog holding an exclude-only policy is scanned, as is one whose namespace holds a policy; ``c`` is not."""
    assert client.attach("nothing", "catalog", ["a"]).status_code == 200
    assert client.attach("sales", "namespace", ["b", "ns"]).status_code == 200

    response = client.client.get("/v1/scanned-catalogs")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "catalogs": [
            {"catalog": "a", "last_discovered_at": None, "failure": None},
            {"catalog": "b", "last_discovered_at": None, "failure": None},
        ]
    }


def test_scanned_catalogs_are_sorted_by_name(client: DiscoveryPolicyWebWorld) -> None:
    """Every scanned catalog is listed once, by name."""
    client.attach("sales", "catalog", ["c"])
    client.attach("sales", "namespace", ["b", "ns"])
    client.attach("sales", "catalog", ["b"])

    names = [c["catalog"] for c in client.client.get("/v1/scanned-catalogs").json()["catalogs"]]

    assert names == ["b", "c"]


def test_scanned_catalogs_show_the_current_failure(client: DiscoveryPolicyWebWorld) -> None:
    """A failure newer than the last scan is shown; one a later scan superseded is not, and the scan time is."""
    client.attach("sales", "catalog", ["b"])
    client.attach("sales", "catalog", ["c"])
    refused = CatalogScanFailure(reason=CatalogScanFailureReason.CANNOT_ACCESS, detail=REFUSED, failed_at=LATER)
    client.discoveries.save(CatalogDiscovery.first("b", NOW))
    client.discoveries.save(CatalogDiscovery.failed("b", refused))
    client.discoveries.save(CatalogDiscovery.failed("c", refused.with_changes(failed_at=NOW)))
    client.discoveries.save(CatalogDiscovery.first("c", LATER))

    body = client.client.get("/v1/scanned-catalogs").json()

    assert body == {
        "catalogs": [
            {
                "catalog": "b",
                "last_discovered_at": _iso(NOW),
                "failure": {"reason": "cannot_access", "detail": REFUSED, "failed_at": _iso(LATER)},
            },
            {"catalog": "c", "last_discovered_at": _iso(LATER), "failure": None},
        ]
    }


def test_a_discovery_of_a_catalog_no_longer_scanned_is_not_listed(client: DiscoveryPolicyWebWorld) -> None:
    """A catalog's record stays after its last managing policy goes, but it is no longer a scanned catalog."""
    client.discoveries.save(CatalogDiscovery.first("a", NOW))

    assert client.client.get("/v1/scanned-catalogs").json() == {"catalogs": []}
