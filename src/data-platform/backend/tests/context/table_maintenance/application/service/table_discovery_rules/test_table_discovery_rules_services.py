"""Test the discovery rules services: read, replace whole and discover, preview, covered catalogs."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.exceptions import ConflictError, ValidationError
from context.table_maintenance.application.port.inbound.table_discovery_rules import (
    GetTableDiscoveryRulesUseCaseInput,
    ListCoveredCatalogsUseCaseInput,
    PreviewTableDiscoveryRulesUseCaseInput,
    PreviewTableDiscoveryRulesUseCaseInputItem,
    PreviewTableDiscoveryRulesUseCaseOutputItem,
    ReplaceTableDiscoveryRulesUseCaseInput,
    ReplaceTableDiscoveryRulesUseCaseInputItem,
)
from context.table_maintenance.application.service.table_discovery_rules import (
    GetTableDiscoveryRulesService,
    ListCoveredCatalogsService,
    PreviewTableDiscoveryRulesService,
    ReplaceTableDiscoveryRulesService,
)

COVERED = ("iceberg", "lake")


def _item(rid=None, priority=10, action="include", *, enabled=True, catalogs=("*",), namespaces=("*",), tables=("*",)):
    return ReplaceTableDiscoveryRulesUseCaseInputItem(
        id=rid,
        priority=priority,
        action=action,
        enabled=enabled,
        catalogs=list(catalogs),
        namespaces=list(namespaces),
        tables=list(tables),
    )


def _preview_item(rid=None, priority=10, action="include", *, tables=("*",), namespaces=("*",)):
    return PreviewTableDiscoveryRulesUseCaseInputItem(
        id=rid,
        priority=priority,
        action=action,
        enabled=True,
        catalogs=["*"],
        namespaces=list(namespaces),
        tables=list(tables),
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
    assert (out.version, out.rules) == (0, [])


def test_save_stores_the_whole_list_in_priority_order(replace, get, now):
    """A save stores every rule in priority order as the next version; rules without an id get one."""
    out = replace.execute(
        ReplaceTableDiscoveryRulesUseCaseInput(
            version=0,
            rules=[
                _item(priority=20, tables=("orders", "tmp_*")),
                _item("keep-me", priority=10, action="exclude", namespaces=("prod.*",)),
            ],
        )
    )
    assert out.version == 1
    assert [(r.id, r.priority, r.action) for r in out.rules] == [("keep-me", 10, "exclude"), ("id-1", 20, "include")]
    assert out.rules[1].tables == ["orders", "tmp_*"]
    assert (out.rules[0].created_at, out.rules[0].updated_at) == (now, now)
    stored = get.execute(GetTableDiscoveryRulesUseCaseInput())
    assert stored.version == out.version
    assert [vars(r) for r in stored.rules] == [vars(r) for r in out.rules]


def test_save_discovers_each_covered_catalog_once(replace, discovery_requests):
    """After a save, one discovery run is started per covered catalog, catalog-wide."""
    replace.execute(ReplaceTableDiscoveryRulesUseCaseInput(version=0, rules=[_item()]))
    assert [(c.catalog, c.namespace) for c in discovery_requests.calls] == [("iceberg", None), ("lake", None)]


def test_equal_priorities_rejected_and_nothing_saved_or_discovered(replace, get, discovery_requests):
    """Two rules with one priority answer a validation error; nothing is saved and nothing discovered."""
    with pytest.raises(ValidationError, match="priority 10"):
        replace.execute(ReplaceTableDiscoveryRulesUseCaseInput(version=0, rules=[_item(), _item()]))
    assert get.execute(GetTableDiscoveryRulesUseCaseInput()).version == 0
    assert discovery_requests.calls == []


def test_stale_version_conflicts(replace, get, discovery_requests):
    """A save from a version that is no longer current conflicts and changes nothing."""
    replace.execute(ReplaceTableDiscoveryRulesUseCaseInput(version=0, rules=[_item("a")]))
    discovery_requests.calls.clear()
    with pytest.raises(ConflictError, match="version 1, not 0"):
        replace.execute(ReplaceTableDiscoveryRulesUseCaseInput(version=0, rules=[]))
    stored = get.execute(GetTableDiscoveryRulesUseCaseInput())
    assert (stored.version, [r.id for r in stored.rules]) == (1, ["a"])
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
        replace.execute(ReplaceTableDiscoveryRulesUseCaseInput(version=0, rules=[item]))
    assert discovery_requests.calls == []


def test_save_with_no_rules_empties_the_list(replace, get):
    """Saving an empty list removes every rule."""
    replace.execute(ReplaceTableDiscoveryRulesUseCaseInput(version=0, rules=[_item("a")]))
    out = replace.execute(ReplaceTableDiscoveryRulesUseCaseInput(version=1, rules=[]))
    assert (out.version, out.rules) == (2, [])
    assert get.execute(GetTableDiscoveryRulesUseCaseInput()).rules == []


def test_preview_reports_deciding_rule_and_writes_nothing(rules_repo, catalog, tables_repo, discovery_requests):
    """Preview decides every table of every covered catalog by the candidate rules and stores nothing."""
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    catalog.add_table("iceberg", "sales", "tmp_x", "u-2")
    catalog.add_table("lake", "prod.eu", "events", "u-3")
    catalog.add_table("other", "sales", "uncovered", "u-4")
    preview = PreviewTableDiscoveryRulesService(catalog, COVERED)
    out = preview.execute(
        PreviewTableDiscoveryRulesUseCaseInput(
            rules=[
                _preview_item(priority=20, namespaces=("sales",)),
                _preview_item("saved-ex", priority=10, action="exclude", tables=("tmp_*",)),
            ]
        )
    )
    assert out.tables == [
        PreviewTableDiscoveryRulesUseCaseOutputItem("iceberg", "sales", "orders", "#0", True),
        PreviewTableDiscoveryRulesUseCaseOutputItem("iceberg", "sales", "tmp_x", "saved-ex", False),
        PreviewTableDiscoveryRulesUseCaseOutputItem("lake", "prod.eu", "events", None, False),
    ]
    assert (out.managed, out.unmanaged) == (1, 2)
    assert rules_repo.get_rules().version == 0
    assert tables_repo.list_all() == []
    assert discovery_requests.calls == []
    assert {name for name, _ in catalog.calls} == {"list_tables"}


def test_preview_rejects_equal_priorities(catalog):
    """A candidate list with two equal priorities is a validation error."""
    preview = PreviewTableDiscoveryRulesService(catalog, COVERED)
    with pytest.raises(ValidationError, match="priority 10"):
        preview.execute(PreviewTableDiscoveryRulesUseCaseInput(rules=[_preview_item(), _preview_item()]))


def test_list_covered_catalogs_returns_configured_names():
    """The covered catalogs are the configured catalog names, in order."""
    out = ListCoveredCatalogsService(COVERED).execute(ListCoveredCatalogsUseCaseInput())
    assert out.catalogs == ["iceberg", "lake"]
