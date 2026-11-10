"""Test the view use cases against the in-memory views repo."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from context.catalog.application.exceptions import ConflictError, NotFoundError, ValidationError
from context.catalog.application.port.inbound.view import (
    CreateViewUseCaseInput,
    DeleteViewUseCaseInput,
    GetViewUseCaseInput,
    ListViewsUseCaseInput,
    ListViewsUseCaseOutputItem,
)
from context.catalog.application.service.view import (
    CreateViewService,
    DeleteViewService,
    GetViewService,
    ListViewsService,
    view_id_from_parts,
)

if TYPE_CHECKING:
    from tests.context.catalog.fakes.in_memory_views_repo import InMemoryViewsRepo

NOW = datetime(2025, 11, 7, 12, 0, tzinfo=UTC)
NOW_MS = int(NOW.timestamp() * 1000)
FORM = CreateViewUseCaseInput(
    catalog="sales", namespace=["retail", "a.b"], name="top_orders", query="SELECT 1", dialect="spark"
)


def _create(repo: InMemoryViewsRepo, form: CreateViewUseCaseInput = FORM):
    return CreateViewService(repo, clock=lambda: NOW).execute(form)


def test_create_defines_version_one_in_the_namespace_at_the_clock_time(views_repo: InMemoryViewsRepo):
    """The created view has one version with the sql and dialect, the namespace as default namespace and the time."""
    created = _create(views_repo)

    assert (created.catalog, created.namespace, created.name) == ("sales", ["retail", "a.b"], "top_orders")
    assert (created.query, created.dialect, created.default_namespace) == ("SELECT 1", "spark", ["retail", "a.b"])
    assert created.versions == [{"version_id": 1, "timestamp_ms": NOW_MS, "query": "SELECT 1"}]
    assert created.uuid == "view-uuid-1"
    assert created.schema == {"schema_id": 0, "fields": []}
    assert created.properties == {}


def test_create_refuses_blank_sql_dialect_and_name(views_repo: InMemoryViewsRepo):
    """Every field of the form is required."""
    with pytest.raises(ValidationError, match="query"):
        _create(views_repo, replace(FORM, query=" "))
    with pytest.raises(ValidationError, match="dialect"):
        _create(views_repo, replace(FORM, dialect=""))
    with pytest.raises(ValidationError, match="name"):
        _create(views_repo, replace(FORM, name=" "))
    assert views_repo.items == {}


def test_create_twice_conflicts(views_repo: InMemoryViewsRepo):
    """The catalog's conflict for a taken name passes through."""
    _create(views_repo)

    with pytest.raises(ConflictError):
        _create(views_repo)


def test_get_returns_the_view_and_unknown_is_not_found(views_repo: InMemoryViewsRepo):
    """Get reads back what create saved; an absent view is NotFoundError."""
    created = _create(views_repo)
    service = GetViewService(views_repo)

    assert vars(service.execute(GetViewUseCaseInput("sales", ["retail", "a.b"], "top_orders"))) == vars(created)
    with pytest.raises(NotFoundError, match="missing"):
        service.execute(GetViewUseCaseInput("sales", ["retail", "a.b"], "missing"))


def test_list_returns_the_identities_in_one_namespace_only(views_repo: InMemoryViewsRepo):
    """Only the views directly in the namespace are listed."""
    _create(views_repo)
    _create(views_repo, replace(FORM, namespace=["other"], name="x"))

    output = ListViewsService(views_repo).execute(ListViewsUseCaseInput("sales", ["retail", "a.b"]))

    assert output.items == [ListViewsUseCaseOutputItem("sales", ["retail", "a.b"], "top_orders")]


def test_delete_removes_the_view_and_unknown_is_not_found(views_repo: InMemoryViewsRepo):
    """Delete drops it; deleting again raises NotFoundError."""
    _create(views_repo)
    service = DeleteViewService(views_repo)

    service.execute(DeleteViewUseCaseInput("sales", ["retail", "a.b"], "top_orders"))

    assert views_repo.items == {}
    with pytest.raises(NotFoundError):
        service.execute(DeleteViewUseCaseInput("sales", ["retail", "a.b"], "top_orders"))


@pytest.mark.parametrize(
    ("catalog", "namespace", "name"),
    [("a\x1fb", ["c"], "t"), ("sales", ["a\x1fb"], "t"), ("sales", ["a"], "t\x1fu")],
)
def test_view_id_from_parts_refuses_the_unit_separator_anywhere(catalog: str, namespace: list[str], name: str):
    """U+001F in the catalog, a part or the name is a validation error, never another object's id."""
    with pytest.raises(ValidationError, match="must not contain the unit separator U\\+001F"):
        view_id_from_parts(catalog, namespace, name)
