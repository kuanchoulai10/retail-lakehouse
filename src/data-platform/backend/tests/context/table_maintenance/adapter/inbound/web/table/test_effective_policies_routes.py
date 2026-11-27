"""Test the effective-policies routes over the real services on in-memory fakes."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    CreateTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.service.table_discovery_policy import CreateTableDiscoveryPolicyService
from tests.context.table_maintenance.adapter.inbound.web.effective_policies_web_world import (
    NOW,
    SALES_TABLES_RULES,
    EffectivePoliciesWebWorld,
)
from tests.context.table_maintenance.discovery_decision_samples import SAMPLE_POLICY_ID

ORDERS = ["prod", "sales", "eu", "orders"]
RETURNS = ["prod", "sales", "eu", "returns"]


@pytest.fixture
def world() -> EffectivePoliciesWebWorld:
    """Provide a client over both kinds of policy and the catalog prod."""
    return EffectivePoliciesWebWorld()


def test_by_uuid_answers_one_entry_per_kind_in_order(world: EffectivePoliciesWebWorld) -> None:
    """GET /tables/{uuid}/effective-policies lists maintenance then discovery, each from its own level."""
    maintenance = world.attach_maintenance("gold", "table", ORDERS)
    discovery = world.attach_discovery("sales-tables", "namespace", ["prod", "sales"])

    response = world.client.get("/v1/tables/u-1/effective-policies")

    assert response.status_code == 200, response.text
    maintenance_entry, discovery_entry = response.json()["policies"]
    assert maintenance_entry == {
        "kind": "maintenance",
        "policy_id": maintenance["policy_id"],
        "policy_name": "gold",
        "version": 1,
        "description": "Platform default",
        "dry_run": True,
        "target": {"type": "table", "path": ORDERS, "table_uuid": "u-1"},
        "attachment_id": maintenance["id"],
    }
    assert discovery_entry == {
        "kind": "discovery",
        "policy_id": discovery["policy_id"],
        "policy_name": "sales-tables",
        "version": 1,
        "description": "Sales tables",
        "target": {"type": "namespace", "path": ["prod", "sales"], "table_uuid": None},
    }


def test_by_uuid_with_nothing_attached_answers_the_default_and_no_discovery_policy(
    world: EffectivePoliciesWebWorld,
) -> None:
    """Maintenance answers its platform default; discovery answers that no policy applies, every field null."""
    policies = world.client.get("/v1/tables/u-1/effective-policies").json()["policies"]

    assert [(p["kind"], p["policy_id"], p["policy_name"], p["target"]) for p in policies] == [
        ("maintenance", "mp-00000000000000000000000000", "default", None),
        ("discovery", None, None, None),
    ]
    assert policies[0]["attachment_id"] is None
    assert policies[0]["dry_run"] is False
    assert policies[1] == {
        "kind": "discovery",
        "policy_id": None,
        "policy_name": None,
        "version": None,
        "description": None,
        "target": None,
    }


def test_the_discovery_entry_answers_the_policys_latest_version(world: EffectivePoliciesWebWorld) -> None:
    """Revising the attached discovery policy moves the entry to the new version."""
    world.attach_discovery("sales-tables", "catalog", ["prod"])
    world.update_discovery("sales-tables", 1, description="Sales v2")

    _, discovery = world.client.get("/v1/tables/u-1/effective-policies").json()["policies"]

    assert (discovery["version"], discovery["description"]) == (2, "Sales v2")


def test_by_uuid_a_table_without_a_record_is_404(world: EffectivePoliciesWebWorld) -> None:
    """A uuid table maintenance has no record of answers 404, though the catalog holds the table."""
    assert world.client.get("/v1/tables/u-2/effective-policies").status_code == 404


def test_by_location_answers_a_table_without_a_record(world: EffectivePoliciesWebWorld) -> None:
    """GET /effective-policies places an unrecorded table by the catalog and finds its own attachments."""
    maintenance = world.attach_maintenance("gold", "table", RETURNS)
    world.attach_discovery("sales-tables", "table", RETURNS)

    response = world.client.get(
        "/v1/effective-policies", params={"catalog": "prod", "namespace": "sales.eu", "table": "returns"}
    )

    assert response.status_code == 200, response.text
    policies = response.json()["policies"]
    assert [p["kind"] for p in policies] == ["maintenance", "discovery"]
    assert policies[0]["attachment_id"] == maintenance["id"]
    assert policies[1]["policy_name"] == "sales-tables"
    assert "attachment_id" not in policies[1]
    assert [p["target"] for p in policies] == [{"type": "table", "path": RETURNS, "table_uuid": "u-2"}] * 2


def test_by_location_answers_a_namespace_and_a_catalog(world: EffectivePoliciesWebWorld) -> None:
    """A dot-joined namespace and a catalog are answered from their own level up."""
    world.attach_maintenance("gold", "catalog", ["prod"])
    world.attach_discovery("sales-tables", "namespace", ["prod", "sales"])

    namespace = world.client.get("/v1/effective-policies", params={"catalog": "prod", "namespace": "sales.eu"})
    catalog = world.client.get("/v1/effective-policies", params={"catalog": "prod"})

    assert [p["target"]["path"] for p in namespace.json()["policies"]] == [["prod"], ["prod", "sales"]]
    assert [(p["policy_name"], p["target"]) for p in catalog.json()["policies"]] == [
        ("gold", {"type": "catalog", "path": ["prod"], "table_uuid": None}),
        (None, None),
    ]


@pytest.mark.parametrize(
    ("path", "params"),
    [
        ("/v1/tables/u-1/effective-policies", None),
        ("/v1/effective-policies", {"catalog": "prod", "namespace": "sales.eu", "table": "returns"}),
        ("/v1/effective-policies", {"catalog": "prod", "namespace": "sales.eu"}),
    ],
)
def test_the_discovery_entry_is_the_deepest_namespace_over_the_catalog(
    world: EffectivePoliciesWebWorld, path: str, params: dict[str, str] | None
) -> None:
    """When ``prod.sales.eu`` and ``prod`` both hold a discovery policy, the namespace's answers."""
    CreateTableDiscoveryPolicyService(world.discovery_policies, clock=lambda: NOW).execute(
        CreateTableDiscoveryPolicyUseCaseInput(name="eu-tables", description="EU tables", rules=SALES_TABLES_RULES)
    )
    world.attach_discovery("sales-tables", "catalog", ["prod"])
    world.attach_discovery("eu-tables", "namespace", ["prod", "sales", "eu"])

    response = world.client.get(path, params=params)

    assert response.status_code == 200, response.text
    discovery = response.json()["policies"][1]
    assert (discovery["policy_name"], discovery["description"], discovery["target"]) == (
        "eu-tables",
        "EU tables",
        {"type": "namespace", "path": ["prod", "sales", "eu"], "table_uuid": None},
    )


@pytest.mark.parametrize(
    "params",
    [
        {"catalog": "gone"},
        {"catalog": "prod", "namespace": "nowhere"},
        {"catalog": "prod", "namespace": "sales.eu", "table": "missing"},
    ],
)
def test_by_location_a_missing_place_is_404(world: EffectivePoliciesWebWorld, params: dict[str, str]) -> None:
    """A catalog, namespace or table the catalog does not hold answers 404."""
    assert world.client.get("/v1/effective-policies", params=params).status_code == 404


@pytest.mark.parametrize(
    "params",
    [
        {"catalog": "prod"},
        {"catalog": "prod", "namespace": "sales.eu"},
        {"catalog": "prod", "namespace": "sales.eu", "table": "orders"},
    ],
)
def test_by_location_a_refused_catalog_is_403(world: EffectivePoliciesWebWorld, params: dict[str, str]) -> None:
    """A catalog the platform cannot read answers 403, as attach does."""
    world.catalog.deny("prod")

    assert world.client.get("/v1/effective-policies", params=params).status_code == 403


@pytest.mark.parametrize("params", [{}, {"namespace": "sales.eu"}, {"catalog": "prod", "table": "orders"}])
def test_by_location_without_a_catalog_or_a_namespace_for_a_table_is_422(
    world: EffectivePoliciesWebWorld, params: dict[str, str]
) -> None:
    """A request naming no catalog, or a table without its namespace, answers 422."""
    assert world.client.get("/v1/effective-policies", params=params).status_code == 422


def test_a_table_shows_what_decided_it(world: EffectivePoliciesWebWorld) -> None:
    """GET /tables/{uuid} answers the policy, version and rule position that decided the table."""
    body = world.client.get("/v1/tables/u-1").json()

    assert body["decided_by"] == {"policy_id": SAMPLE_POLICY_ID.value, "policy_version": 1, "rule_position": 1}
