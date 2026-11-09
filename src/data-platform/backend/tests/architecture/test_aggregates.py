"""Guard tests: a context's aggregates are derived from its domain model."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from tests.architecture.aggregates import aggregates, derive_aggregates
from tests.architecture.fixture_context import build_fixture_context

if TYPE_CHECKING:
    import pytest

ARCHITECTURE_TESTS = Path(__file__).resolve().parent
CONCRETE_CONTEXT_MARKERS = (
    '"table_maintenance"',
    "'table_maintenance'",
    "context.table_maintenance",
    "context/table_maintenance",
    "context.catalog",
    "context/catalog",
)

WIDGET = '''"""Widget aggregate."""

from __future__ import annotations

from dataclasses import dataclass

from base import AggregateRoot, EntityId


@dataclass(frozen=True)
class WidgetId(EntityId):
    """Identify a widget."""


class Widget(AggregateRoot[WidgetId]):
    """A widget."""
'''

STRAY = '''"""Not an aggregate: a plain dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Stray:
    """A stray value."""

    value: int
'''

SHARED = '''"""Shared kernel of the model: never an aggregate, even with a root in it."""

from __future__ import annotations

from dataclasses import dataclass

from base import AggregateRoot, EntityId


@dataclass(frozen=True)
class SharedId(EntityId):
    """Identify a shared thing."""


class SharedThing(AggregateRoot[SharedId]):
    """A shared thing."""
'''


def test_table_maintenance_aggregates_are_derived():
    """The table maintenance context derives its six aggregates from the domain model."""
    assert aggregates("table_maintenance") == {
        "table",
        "table_maintenance_run",
        "table_reconciliation",
        "table_maintenance_preset",
        "table_discovery_rule",
        "table_discovery_settings",
    }


def test_catalog_aggregates_are_derived():
    """The catalog context derives its aggregates from the domain model."""
    assert aggregates("catalog") == {"catalog", "namespace", "table", "generic_table", "view"}


def test_package_without_aggregate_root_is_not_an_aggregate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A model package without an aggregate root class is not counted as an aggregate."""
    name = build_fixture_context(
        tmp_path,
        {
            "application/domain/model/widget/__init__.py": WIDGET,
            "application/domain/model/stray/__init__.py": STRAY,
            "application/domain/model/shared/__init__.py": SHARED,
        },
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    assert derive_aggregates(f"{name}.application.domain.model") == {"widget"}


def test_architecture_tests_name_no_context():
    """A rule that names one context would silently skip every other context."""
    offenders = [
        f"{path.name}: {marker}"
        for path in sorted(ARCHITECTURE_TESTS.glob("*.py"))
        if path.name != Path(__file__).name
        for marker in CONCRETE_CONTEXT_MARKERS
        if marker in path.read_text()
    ]
    assert offenders == [], "\n".join(offenders)
