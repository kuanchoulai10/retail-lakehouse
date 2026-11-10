"""Test the generic table use cases against the in-memory generic tables repo."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from context.catalog.application.exceptions import ConflictError, NotFoundError, ValidationError
from context.catalog.application.port.inbound.generic_table import (
    CreateGenericTableUseCaseInput,
    DeleteGenericTableUseCaseInput,
    GetGenericTableUseCaseInput,
    ListGenericTablesUseCaseInput,
    ListGenericTablesUseCaseOutputItem,
)
from context.catalog.application.service.generic_table import (
    CreateGenericTableService,
    DeleteGenericTableService,
    GetGenericTableService,
    ListGenericTablesService,
    generic_table_id_from_parts,
)

if TYPE_CHECKING:
    from tests.context.catalog.fakes.in_memory_generic_tables_repo import InMemoryGenericTablesRepo

FORM = CreateGenericTableUseCaseInput(
    catalog="sales",
    namespace=["retail"],
    name="events",
    format="delta",
    base_location="s3://w/events",
    doc="clicks",
    properties={"owner": "data-eng"},
)


def test_create_then_get_returns_the_generic_table(generic_tables_repo: InMemoryGenericTablesRepo):
    """A created generic table reads back with format, base location, doc and properties."""
    created = CreateGenericTableService(generic_tables_repo).execute(FORM)

    fetched = GetGenericTableService(generic_tables_repo).execute(
        GetGenericTableUseCaseInput("sales", ["retail"], "events")
    )

    assert vars(fetched) == vars(created)
    assert (fetched.catalog, fetched.namespace, fetched.name) == ("sales", ["retail"], "events")
    assert (fetched.format, fetched.base_location, fetched.doc, fetched.properties) == (
        "delta",
        "s3://w/events",
        "clicks",
        {"owner": "data-eng"},
    )


def test_create_turns_blank_optional_text_into_none(generic_tables_repo: InMemoryGenericTablesRepo):
    """A blank base location or doc is absent, not an empty string sent to the catalog."""
    created = CreateGenericTableService(generic_tables_repo).execute(replace(FORM, base_location="  ", doc=""))

    assert (created.base_location, created.doc) == (None, None)


def test_create_refuses_a_blank_format_and_a_blank_name(generic_tables_repo: InMemoryGenericTablesRepo):
    """Polaris needs a format and a name; the form is refused before it is sent."""
    service = CreateGenericTableService(generic_tables_repo)

    with pytest.raises(ValidationError, match="format"):
        service.execute(replace(FORM, format=" "))
    with pytest.raises(ValidationError, match="name"):
        service.execute(replace(FORM, name=" "))
    assert generic_tables_repo.items == {}


def test_create_twice_conflicts(generic_tables_repo: InMemoryGenericTablesRepo):
    """The catalog's conflict for a taken name passes through."""
    service = CreateGenericTableService(generic_tables_repo)
    service.execute(FORM)

    with pytest.raises(ConflictError):
        service.execute(FORM)


def test_get_unknown_generic_table_is_not_found(generic_tables_repo: InMemoryGenericTablesRepo):
    """An absent generic table is NotFoundError naming it."""
    with pytest.raises(NotFoundError, match="events"):
        GetGenericTableService(generic_tables_repo).execute(GetGenericTableUseCaseInput("sales", ["retail"], "events"))


def test_list_returns_the_identities_in_one_namespace_only(generic_tables_repo: InMemoryGenericTablesRepo):
    """Only the generic tables directly in the namespace are listed."""
    create = CreateGenericTableService(generic_tables_repo)
    create.execute(FORM)
    create.execute(replace(FORM, namespace=["other"], name="x"))

    output = ListGenericTablesService(generic_tables_repo).execute(ListGenericTablesUseCaseInput("sales", ["retail"]))

    assert output.items == [ListGenericTablesUseCaseOutputItem("sales", ["retail"], "events")]


def test_delete_removes_the_generic_table_and_unknown_is_not_found(generic_tables_repo: InMemoryGenericTablesRepo):
    """Delete drops it; deleting again raises NotFoundError."""
    CreateGenericTableService(generic_tables_repo).execute(FORM)
    service = DeleteGenericTableService(generic_tables_repo)

    service.execute(DeleteGenericTableUseCaseInput("sales", ["retail"], "events"))

    assert generic_tables_repo.items == {}
    with pytest.raises(NotFoundError):
        service.execute(DeleteGenericTableUseCaseInput("sales", ["retail"], "events"))


@pytest.mark.parametrize(
    ("catalog", "namespace", "name"),
    [("a\x1fb", ["c"], "t"), ("sales", ["a\x1fb"], "t"), ("sales", ["a"], "t\x1fu")],
)
def test_generic_table_id_from_parts_refuses_the_unit_separator_anywhere(catalog: str, namespace: list[str], name: str):
    """U+001F in the catalog, a part or the name is a validation error, never another object's id."""
    with pytest.raises(ValidationError, match="must not contain the unit separator U\\+001F"):
        generic_table_id_from_parts(catalog, namespace, name)
