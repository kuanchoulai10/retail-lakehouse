"""Test the ViewId identifier, the View aggregate and its versions."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from context.catalog.application.domain.model.shared import Schema
from context.catalog.application.domain.model.view import View, ViewId, ViewVersion

VIEW_ID = ViewId.of("sales", ("retail",), "top_orders")


def test_view_id_joins_catalog_namespace_and_name_with_the_unit_separator():
    """The value is the catalog, the namespace parts and the name, joined by U+001F."""
    view_id = ViewId.of("sales", ("a", "b.c"), "v")

    assert view_id.value == "sales\x1fa\x1fb.c\x1fv"
    assert (view_id.catalog, view_id.namespace, view_id.name) == ("sales", ("a", "b.c"), "v")


def test_defined_view_has_one_version_and_no_catalog_assigned_facts():
    """A view defined for create has version 1 holding the sql; the catalog assigns its uuid and location."""
    view = View.define(
        id=VIEW_ID,
        query="SELECT 1",
        dialect="spark",
        default_namespace=("retail",),
        timestamp_ms=1762516800000,
    )

    assert (view.uuid, view.location) == (None, None)
    assert view.current_schema == Schema(schema_id=0, fields=())
    assert view.versions == [
        ViewVersion(
            version_id=1,
            timestamp_ms=1762516800000,
            schema_id=0,
            query="SELECT 1",
            dialect="spark",
            default_namespace=("retail",),
        )
    ]
    assert view.current_version.version_id == 1
    assert (view.query, view.dialect, view.default_namespace) == ("SELECT 1", "spark", ("retail",))


def test_current_version_is_the_version_the_view_points_at():
    """The view's sql is the sql of the current version, not the latest or the first."""
    older = ViewVersion(
        version_id=1, timestamp_ms=10, schema_id=0, query="SELECT 1", dialect="spark", default_namespace=("retail",)
    )
    newer = ViewVersion(
        version_id=2, timestamp_ms=20, schema_id=0, query="SELECT 2", dialect="trino", default_namespace=("retail", "x")
    )
    view = View(
        id=VIEW_ID,
        uuid="u",
        location="s3://w/v",
        current_schema=Schema(schema_id=0, fields=()),
        current_version_id=1,
        versions=[older, newer],
        properties={},
    )

    assert view.current_version == older
    assert (view.query, view.dialect) == ("SELECT 1", "spark")


def test_view_pointing_at_no_version_is_refused():
    """A current version id with no matching version raises instead of answering an empty view."""
    view = View(
        id=VIEW_ID,
        uuid="u",
        location="s3://w/v",
        current_schema=Schema(schema_id=0, fields=()),
        current_version_id=9,
        versions=[
            ViewVersion(
                version_id=1,
                timestamp_ms=10,
                schema_id=0,
                query="SELECT 1",
                dialect="spark",
                default_namespace=("retail",),
            )
        ],
        properties={},
    )

    with pytest.raises(ValueError, match="current version 9"):
        _ = view.current_version


@pytest.mark.parametrize(
    ("catalog", "namespace", "name", "message"),
    [
        ("a\x1fb", ("c",), "t", "catalog name must not contain"),
        ("sales", ("a\x1fb",), "t", "namespace parts must not contain"),
        ("sales", ("a",), "t\x1fu", "view name must not contain"),
    ],
)
def test_view_id_refuses_the_unit_separator_inside_any_component(catalog, namespace, name, message):
    """A U+001F inside the catalog, a namespace part or the name would split differently, so it is refused."""
    with pytest.raises(ValueError, match=message):
        ViewId.of(catalog, namespace, name)


def _view() -> View:
    return View.define(
        id=VIEW_ID, query="SELECT 1", dialect="spark", default_namespace=("retail",), timestamp_ms=1762516800000
    )


def test_view_version_requires_keywords():
    """A view version is built by field name; positional values are refused."""
    with pytest.raises(TypeError):
        ViewVersion(1, 10, 0, "SELECT 1", "spark", ("retail",))  # ty: ignore[too-many-positional-arguments, missing-argument]


def test_view_version_is_immutable_and_strict():
    """A view version cannot change, and a list is not its tuple of namespace parts."""
    version = ViewVersion(
        version_id=1, timestamp_ms=10, schema_id=0, query="SELECT 1", dialect="spark", default_namespace=("retail",)
    )

    with pytest.raises(ValidationError):
        version.query = "SELECT 2"
    with pytest.raises(ValidationError):
        ViewVersion(
            version_id=1,
            timestamp_ms=10,
            schema_id=0,
            query="SELECT 1",
            dialect="spark",
            default_namespace=["retail"],  # ty: ignore[invalid-argument-type]
        )
    with pytest.raises(ValidationError):
        ViewVersion(
            version_id=True,
            timestamp_ms=10,
            schema_id=0,
            query="SELECT 1",
            dialect="spark",
            default_namespace=("retail",),
        )


def test_view_id_is_built_positionally_and_strict():
    """The id keeps its positional form and takes only a string."""
    assert ViewId("sales\x1fretail\x1ftop_orders") == VIEW_ID
    with pytest.raises(ValidationError):
        ViewId(1)  # ty: ignore[invalid-argument-type]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("uuid", 1),
        ("location", b"s3://w/v"),
        ("current_schema", "schema 0"),
        ("current_version_id", "1"),
        ("versions", ({"version_id": 1},)),
        ("properties", {"a": 1}),
    ],
)
def test_assigning_a_wrong_type_is_rejected_and_changes_nothing(field: str, value: object):
    """Every assignment is validated strictly; a rejected one leaves the view as it was."""
    view = _view()
    before = view.model_dump()

    with pytest.raises(ValidationError):
        setattr(view, field, value)

    assert view.model_dump() == before
