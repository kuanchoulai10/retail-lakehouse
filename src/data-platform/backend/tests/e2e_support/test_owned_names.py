"""Test OwnedNames, the names the e2e gives what it creates and how a later run recognizes them."""

from __future__ import annotations

import pytest

from e2e.support import OwnedNames

SUFFIX = "1a2b3c4d"


def test_every_name_a_run_gives_is_recognized_as_the_e2es():
    """What a scenario creates matches the pattern the sweep removes by."""
    assert OwnedNames.NAMESPACE.match(OwnedNames.namespace(SUFFIX, "orders"))
    assert OwnedNames.MAINTENANCE_POLICY.match(OwnedNames.maintenance_policy(SUFFIX, "orders"))
    assert OwnedNames.DISCOVERY_POLICY.match(OwnedNames.discovery_policy(SUFFIX, "orders"))
    assert OwnedNames.CATALOG.match(OwnedNames.catalog(SUFFIX, "round_trip"))
    assert OwnedNames.QUEUE_HOLDER.match(OwnedNames.queue_holder(SUFFIX, "maintenance_queue"))


def test_the_names_keep_the_shape_the_scenarios_use():
    """Iceberg and Polaris names use underscores, policy names hyphens."""
    assert OwnedNames.namespace(SUFFIX, "orders") == "e2e_1a2b3c4d_orders"
    assert OwnedNames.maintenance_policy(SUFFIX, "orders") == "tm-e2e-orders-1a2b3c4d"
    assert OwnedNames.discovery_policy(SUFFIX, "orders") == "tm-e2e-1a2b3c4d-orders"
    assert OwnedNames.catalog(SUFFIX, "round_trip") == "tm_e2e_catalog_1a2b3c4d_round_trip"
    assert OwnedNames.queue_holder(SUFFIX, "maintenance_queue") == "tm-e2e-holder-1a2b3c4d-maintenance-queue"


@pytest.mark.parametrize(
    "pattern",
    [
        OwnedNames.NAMESPACE,
        OwnedNames.MAINTENANCE_POLICY,
        OwnedNames.DISCOVERY_POLICY,
        OwnedNames.CATALOG,
        OwnedNames.QUEUE_HOLDER,
    ],
)
@pytest.mark.parametrize(
    "name",
    [
        "default",
        "iceberg",
        "inventory",
        "e2e",
        "tm-e2e",
        "tm-e2e-orders",
        "e2e_orders",
        "tm_e2e_catalog_x",
        "tm_e2e_catalog_1a2b3c4d",
    ],
)
def test_names_the_e2e_did_not_give_are_not_its(pattern, name):
    """The platform's own and the retired script's fixed names never match."""
    assert not pattern.match(name)


@pytest.mark.parametrize("scenario", ["v2_lifecycle", "Lifecycle", "", "_x"])
def test_a_scenario_word_the_sweep_could_not_match_is_refused(scenario):
    """A name the sweep's pattern would not match is never handed out, since nothing would remove what it names."""
    for build in (
        OwnedNames.namespace,
        OwnedNames.maintenance_policy,
        OwnedNames.discovery_policy,
        OwnedNames.catalog,
        OwnedNames.queue_holder,
    ):
        with pytest.raises(ValueError, match="scenario word"):
            build(SUFFIX, scenario)
