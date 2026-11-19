"""Test the discovery rules services: read, replace whole and discover, covered catalogs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from context.table_maintenance.application.exceptions import ConflictError, ValidationError
from context.table_maintenance.application.port.inbound.table_discovery_rules import (
    GetTableDiscoveryRulesUseCaseInput,
    ListCoveredCatalogsUseCaseInput,
    ReplaceTableDiscoveryRulesUseCaseInput,
)
from context.table_maintenance.application.port.outbound.table import SendDiscoveryRequestGateway
from context.table_maintenance.application.service.table_discovery_rules import (
    GetTableDiscoveryRulesService,
    ListCoveredCatalogsService,
    ReplaceTableDiscoveryRulesService,
)
from shared_kernel import prefixed_id_pattern

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import SendDiscoveryRequestGatewayInput

COVERED = ("iceberg", "lake")
FIRST_MINTED = "dr-00000000000000000000000001"
SECOND_MINTED = "dr-00000000000000000000000002"
UNKNOWN_RULE = "dr-7zzzzzzzzzzzzzzzzzzzzzzzzz"


class _FailingFor(SendDiscoveryRequestGateway):
    """Fail to start discovery for one catalog and record the rest."""

    def __init__(self, catalog: str) -> None:
        self._catalog = catalog
        self.calls: list[SendDiscoveryRequestGatewayInput] = []

    def send(self, input: SendDiscoveryRequestGatewayInput) -> None:  # noqa: A002
        if input.catalog == self._catalog:
            raise RuntimeError(f"cannot start discovery for {input.catalog}")
        self.calls.append(input)


def _item(rid=None, priority=10, action="include", *, enabled=True, catalogs=("*",), namespaces=("*",), tables=("*",)):
    return ReplaceTableDiscoveryRulesUseCaseInput.TableDiscoveryRule(
        id=rid,
        priority=priority,
        action=action,
        enabled=enabled,
        catalogs=tuple(catalogs),
        namespaces=tuple(namespaces),
        tables=tuple(tables),
    )


@pytest.fixture
def replace(rules_repo, discovery_requests, clock, new_id):
    """Provide the replace discovery rules service on the fakes."""
    return ReplaceTableDiscoveryRulesService(rules_repo, discovery_requests, COVERED, clock=clock, new_id=new_id)


@pytest.fixture
def get(rules_repo):
    """Provide the get discovery rules service on the fakes."""
    return GetTableDiscoveryRulesService(rules_repo)


def test_rules_start_empty_at_version_zero(get):
    """Before any save the rules are empty at version 0."""
    out = get.execute(GetTableDiscoveryRulesUseCaseInput())
    assert (out.version, out.rules) == (0, ())


def test_save_stores_the_whole_list_in_priority_order(replace, get, now):
    """A save stores every rule in priority order as the next version; rules without an id get one."""
    out = replace.execute(
        ReplaceTableDiscoveryRulesUseCaseInput(
            version=0,
            rules=(
                _item(priority=20, tables=("orders", "tmp_*")),
                _item(priority=10, action="exclude", namespaces=("prod.*",)),
            ),
        )
    )
    assert out.version == 1
    assert [(r.id, r.priority, r.action) for r in out.rules] == [
        (SECOND_MINTED, 10, "exclude"),
        (FIRST_MINTED, 20, "include"),
    ]
    assert out.rules[1].tables == ("orders", "tmp_*")
    assert (out.rules[0].created_at, out.rules[0].updated_at) == (now, now)
    stored = get.execute(GetTableDiscoveryRulesUseCaseInput())
    assert stored.version == out.version
    assert [r.model_dump() for r in stored.rules] == [r.model_dump() for r in out.rules]


def test_rule_ids_minted_by_replace_have_the_dr_prefix(rules_repo, discovery_requests):
    """Without an injected generator, each rule saved without an id gets a fresh dr- id of its own."""
    service = ReplaceTableDiscoveryRulesService(rules_repo, discovery_requests, COVERED)
    out = service.execute(ReplaceTableDiscoveryRulesUseCaseInput(version=0, rules=(_item(priority=1), _item())))
    ids = [r.id for r in out.rules]
    assert all(prefixed_id_pattern("dr").fullmatch(rule_id) for rule_id in ids), ids
    assert len(set(ids)) == 2


def test_save_discovers_each_covered_catalog_once(replace, discovery_requests):
    """After a save, one discovery run is started per covered catalog, catalog-wide."""
    replace.execute(ReplaceTableDiscoveryRulesUseCaseInput(version=0, rules=(_item(),)))
    assert [(c.catalog, c.namespace) for c in discovery_requests.calls] == [("iceberg", None), ("lake", None)]


def test_each_save_starts_its_own_discovery_runs(replace, discovery_requests):
    """Two saves in a row each start discovery with their own saved version, so a later save is not lost."""
    replace.execute(ReplaceTableDiscoveryRulesUseCaseInput(version=0, rules=(_item(),)))
    replace.execute(ReplaceTableDiscoveryRulesUseCaseInput(version=1, rules=()))
    assert [(c.catalog, c.rules_version) for c in discovery_requests.calls] == [
        ("iceberg", 1),
        ("lake", 1),
        ("iceberg", 2),
        ("lake", 2),
    ]


def test_a_failed_discovery_start_still_answers_the_saved_rules(rules_repo, clock, new_id, caplog):
    """When starting discovery fails for one catalog, the save still answers its rules and the others are sent."""
    gateway = _FailingFor("iceberg")
    service = ReplaceTableDiscoveryRulesService(rules_repo, gateway, COVERED, clock=clock, new_id=new_id)
    out = service.execute(ReplaceTableDiscoveryRulesUseCaseInput(version=0, rules=(_item(),)))
    assert (out.version, [r.id for r in out.rules]) == (1, [FIRST_MINTED])
    assert [c.catalog for c in gateway.calls] == ["lake"]
    assert "iceberg" in caplog.text


def test_an_id_not_in_the_saved_list_is_rejected(replace, get, discovery_requests):
    """A rule id the stored list does not hold is a validation error; nothing is saved or discovered."""
    with pytest.raises(ValidationError, match=f"unknown discovery rule id {UNKNOWN_RULE}"):
        replace.execute(ReplaceTableDiscoveryRulesUseCaseInput(version=0, rules=(_item(UNKNOWN_RULE),)))
    assert get.execute(GetTableDiscoveryRulesUseCaseInput()).version == 0
    assert discovery_requests.calls == []


def test_equal_priorities_rejected_and_nothing_saved_or_discovered(replace, get, discovery_requests):
    """Two rules with one priority answer a validation error; nothing is saved and nothing discovered."""
    with pytest.raises(ValidationError, match="priority 10"):
        replace.execute(ReplaceTableDiscoveryRulesUseCaseInput(version=0, rules=(_item(), _item())))
    assert get.execute(GetTableDiscoveryRulesUseCaseInput()).version == 0
    assert discovery_requests.calls == []


def test_stale_version_conflicts(replace, get, discovery_requests):
    """A save from a version that is no longer current conflicts and changes nothing."""
    replace.execute(ReplaceTableDiscoveryRulesUseCaseInput(version=0, rules=(_item(),)))
    discovery_requests.calls.clear()
    with pytest.raises(ConflictError, match="version 1, not 0"):
        replace.execute(ReplaceTableDiscoveryRulesUseCaseInput(version=0, rules=()))
    stored = get.execute(GetTableDiscoveryRulesUseCaseInput())
    assert (stored.version, [r.id for r in stored.rules]) == (1, [FIRST_MINTED])
    assert discovery_requests.calls == []


@pytest.mark.parametrize(
    "item",
    [
        _item(action="maybe"),
        _item(tables=()),
        _item(catalogs=("",)),
    ],
    ids=["unknown-action", "no-table-glob", "empty-glob"],
)
def test_invalid_rule_rejected(replace, discovery_requests, item):
    """An unknown action or an empty glob list is a validation error."""
    with pytest.raises(ValidationError):
        replace.execute(ReplaceTableDiscoveryRulesUseCaseInput(version=0, rules=(item,)))
    assert discovery_requests.calls == []


def test_save_with_no_rules_empties_the_list(replace, get):
    """Saving an empty list removes every rule."""
    replace.execute(ReplaceTableDiscoveryRulesUseCaseInput(version=0, rules=(_item(),)))
    out = replace.execute(ReplaceTableDiscoveryRulesUseCaseInput(version=1, rules=()))
    assert (out.version, out.rules) == (2, ())
    assert get.execute(GetTableDiscoveryRulesUseCaseInput()).rules == ()


def test_list_covered_catalogs_returns_configured_names():
    """The covered catalogs are the configured catalog names, in order."""
    out = ListCoveredCatalogsService(COVERED).execute(ListCoveredCatalogsUseCaseInput())
    assert out.catalogs == ("iceberg", "lake")
