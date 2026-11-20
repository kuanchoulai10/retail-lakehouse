"""Test comparing two schemas by Iceberg field id."""

from __future__ import annotations

from context.catalog.application.domain.model.shared import Schema, SchemaField, SchemaFieldKind
from context.catalog.application.domain.model.table import SchemaChange, SchemaFieldComparison
from context.catalog.application.domain.service.table import compare_schemas


def _field(
    field_id: int,
    name: str,
    type_: str,
    *,
    required: bool = False,
    doc: str | None = None,
    kind: SchemaFieldKind = SchemaFieldKind.PRIMITIVE,
    children: tuple[SchemaField, ...] = (),
) -> SchemaField:
    return SchemaField(id=field_id, name=name, type=type_, required=required, doc=doc, kind=kind, children=children)


def _schema(*fields: SchemaField, schema_id: int = 0) -> Schema:
    return Schema(schema_id=schema_id, fields=fields)


def _cmp(base: Schema | None, new: Schema) -> dict[int, SchemaFieldComparison]:
    return {f.field_id: f for f in compare_schemas(base, new).fields}


def _order(base: Schema | None, new: Schema) -> list[int]:
    return [f.field_id for f in compare_schemas(base, new).fields]


def test_added_and_removed_fields():
    """A field only in the new schema is added and one only in the base is removed, each with one side empty."""
    base = _schema(_field(1, "order_id", "long"), _field(3, "order_ts", "timestamp"))
    new = _schema(_field(1, "order_id", "long"), _field(4, "status", "string", required=True, doc="State"), schema_id=1)
    rows = _cmp(base, new)
    assert rows[1].changes == ()
    assert rows[4].changes == (SchemaChange.ADDED,)
    assert (rows[4].path, rows[4].previous_path) == (("status",), None)
    assert (rows[4].type, rows[4].previous_type) == ("string", None)
    assert (rows[4].required, rows[4].previous_required) == (True, None)
    assert (rows[4].doc, rows[4].previous_doc) == ("State", None)
    assert rows[3].changes == (SchemaChange.REMOVED,)
    assert (rows[3].path, rows[3].previous_path) == (None, ("order_ts",))
    assert (rows[3].type, rows[3].previous_type) == (None, "timestamp")
    assert (rows[3].required, rows[3].previous_required) == (None, False)
    comparison = compare_schemas(base, new)
    assert (comparison.base_schema_id, comparison.schema_id) == (0, 1)


def test_rename_is_matched_by_id():
    """A renamed field is one renamed row, never a removal plus an addition."""
    rows = _cmp(_schema(_field(2, "customer_id", "long")), _schema(_field(2, "customer", "long")))
    assert rows[2].changes == (SchemaChange.RENAMED,)
    assert (rows[2].previous_path, rows[2].path) == (("customer_id",), ("customer",))


def test_rename_and_promotion_are_one_row():
    """A field renamed and promoted in one version is one row carrying both changes."""
    rows = _cmp(_schema(_field(2, "customer_id", "int")), _schema(_field(2, "customer", "long")))
    assert list(rows) == [2]
    assert rows[2].changes == (SchemaChange.RENAMED, SchemaChange.TYPE_CHANGED)
    assert (rows[2].previous_type, rows[2].type) == ("int", "long")


def test_nullability_and_doc_changes():
    """A change of requiredness and of doc are reported, in enum order."""
    base = _schema(_field(1, "id", "long", required=True), _field(2, "note", "string", doc=None))
    new = _schema(_field(1, "id", "long", required=False, doc="Primary key"), _field(2, "note", "string", doc=None))
    rows = _cmp(base, new)
    assert rows[1].changes == (SchemaChange.NULLABILITY_CHANGED, SchemaChange.DOC_CHANGED)
    assert (rows[1].previous_required, rows[1].required) == (True, False)
    assert (rows[1].previous_doc, rows[1].doc) == (None, "Primary key")
    assert rows[2].changes == ()


def _shipping(*children: SchemaField, name: str = "shipping") -> SchemaField:
    return _field(7, name, "struct<...>", kind=SchemaFieldKind.STRUCT, children=children)


def test_nested_child_added_shows_full_path():
    """A nested field added to a struct shows its full path and depth; the parent is unchanged."""
    city = _field(8, "city", "string")
    base = _schema(_field(1, "id", "long"), _shipping(city))
    new = _schema(_field(1, "id", "long"), _shipping(city, _field(9, "zip", "string")))
    rows = _cmp(base, new)
    assert rows[9].changes == (SchemaChange.ADDED,)
    assert rows[9].path == ("shipping", "zip")
    assert rows[9].depth == 1
    assert rows[7].changes == ()
    assert rows[7].depth == 0
    assert rows[8].changes == ()


def test_parent_rename_does_not_rename_children():
    """A renamed parent does not mark its children renamed; they show the old path as previous_path."""
    city = _field(8, "city", "string")
    rows = _cmp(_schema(_shipping(city)), _schema(_shipping(city, name="ship_to")))
    assert rows[7].changes == (SchemaChange.RENAMED,)
    assert rows[8].changes == ()
    assert rows[8].path == ("ship_to", "city")
    assert rows[8].previous_path == ("shipping", "city")


def _list(element: SchemaField, *, type_: str) -> SchemaField:
    return _field(5, "tags", type_, kind=SchemaFieldKind.LIST, children=(element,))


def test_list_element_promotion():
    """A list element promoted from int to long changes the element row, not the list row."""
    base = _schema(_list(_field(6, "element", "int"), type_="list<int>"))
    new = _schema(_list(_field(6, "element", "long"), type_="list<long>"))
    rows = _cmp(base, new)
    assert rows[6].changes == (SchemaChange.TYPE_CHANGED,)
    assert rows[6].path == ("tags", "element")
    assert (rows[6].previous_type, rows[6].type) == ("int", "long")
    assert rows[5].changes == ()
    assert rows[5].type == "list"


def test_map_value_promotion_changes_the_value_row_only():
    """A map value promoted from int to long changes the value row; the map and its key are unchanged."""

    def counts(value_type: str) -> SchemaField:
        key = _field(10, "key", "string", required=True)
        value = _field(11, "value", value_type)
        return _field(9, "counts", f"map<string, {value_type}>", kind=SchemaFieldKind.MAP, children=(key, value))

    rows = _cmp(_schema(counts("int")), _schema(counts("long"), schema_id=1))
    assert rows[11].changes == (SchemaChange.TYPE_CHANGED,)
    assert rows[11].path == ("counts", "value")
    assert (rows[11].previous_type, rows[11].type) == ("int", "long")
    assert rows[9].changes == ()
    assert rows[9].type == "map"
    assert rows[10].changes == ()


def test_decimal_precision_widening_is_a_type_change():
    """``decimal(10,2)`` to ``decimal(12,2)`` is a type change carrying both texts."""
    rows = _cmp(_schema(_field(4, "amount", "decimal(10,2)")), _schema(_field(4, "amount", "decimal(12,2)")))
    assert rows[4].changes == (SchemaChange.TYPE_CHANGED,)
    assert (rows[4].previous_type, rows[4].type) == ("decimal(10,2)", "decimal(12,2)")


def test_reordered_columns_change_nothing_and_follow_the_new_order():
    """Moving a column is not a field change: every row is unchanged and rows follow the new order."""
    base = _schema(_field(1, "a", "int"), _field(2, "b", "int"), _field(3, "c", "int"))
    new = _schema(_field(3, "c", "int"), _field(1, "a", "int"), _field(2, "b", "int"), schema_id=1)
    comparison = compare_schemas(base, new)
    assert [f.field_id for f in comparison.fields] == [3, 1, 2]
    assert all(f.changes == () for f in comparison.fields)


def test_removed_fields_follow_their_base_neighbours_after_a_reorder():
    """Each removed field sits after the field before it in the base, wherever that field moved."""
    base = _schema(_field(1, "a", "int"), _field(2, "b", "int"), _field(3, "c", "int"), _field(4, "d", "int"))
    new = _schema(_field(3, "c", "int"), _field(1, "a", "int"), schema_id=1)
    assert _order(base, new) == [3, 4, 1, 2]


def test_removed_field_sits_after_its_former_neighbour():
    """A removed field is placed right after the field that preceded it in the base."""
    base = _schema(_field(1, "a", "int"), _field(2, "b", "int"), _field(3, "c", "int"))
    new = _schema(_field(1, "a", "int"), _field(3, "c", "int"), schema_id=1)
    assert _order(base, new) == [1, 2, 3]


def test_removed_first_field_comes_first():
    """A removed field with no earlier neighbour comes first."""
    base = _schema(_field(1, "a", "int"), _field(2, "b", "int"))
    assert _order(base, _schema(_field(2, "b", "int"), schema_id=1)) == [1, 2]


def test_consecutive_removed_fields_keep_base_order():
    """Consecutive removed fields stay in base order."""
    base = _schema(_field(1, "a", "int"), _field(2, "b", "int"), _field(3, "c", "int"), _field(4, "d", "int"))
    new = _schema(_field(1, "a", "int"), _field(4, "d", "int"), schema_id=1)
    assert _order(base, new) == [1, 2, 3, 4]


def test_removed_nested_child_keeps_its_depth_in_the_base():
    """A removed nested field carries its depth and path from the base."""
    city = _field(8, "city", "string")
    base = _schema(_shipping(city, _field(9, "zip", "string")))
    rows = _cmp(base, _schema(_shipping(city), schema_id=1))
    assert rows[9].changes == (SchemaChange.REMOVED,)
    assert rows[9].depth == 1
    assert rows[9].previous_path == ("shipping", "zip")


def test_all_removed_fields_come_before_an_unrelated_new_field():
    """Removed fields with no surviving neighbour come first, in base order."""
    base = _schema(_field(1, "a", "int"), _field(2, "b", "int"))
    new = _schema(_field(3, "c", "int"), schema_id=1)
    assert _order(base, new) == [1, 2, 3]


def test_no_base_lists_every_field_unchanged():
    """With no base every field is listed unchanged and its previous side equals its current side."""
    new = _schema(_field(1, "id", "long", doc="Key"), _shipping(_field(8, "city", "string")))
    comparison = compare_schemas(None, new)
    assert comparison.base_schema_id is None
    assert [f.field_id for f in comparison.fields] == [1, 7, 8]
    assert all(f.changes == () for f in comparison.fields)
    assert all((f.previous_path, f.previous_type, f.previous_doc) == (f.path, f.type, f.doc) for f in comparison.fields)
    assert all(f.previous_required == f.required for f in comparison.fields)


def test_identical_schemas_have_no_changes():
    """Two identical schemas change nothing and count zero of every kind."""
    both = _schema(_field(1, "id", "long"), _shipping(_field(8, "city", "string")))
    comparison = compare_schemas(both, both)
    assert all(f.changes == () for f in comparison.fields)
    assert set(comparison.change_counts().values()) == {0}


def test_change_counts_cover_every_kind():
    """The change counts list every kind, zeros included."""
    comparison = compare_schemas(_schema(_field(1, "a", "int")), _schema(_field(1, "b", "long"), _field(2, "c", "int")))
    assert comparison.change_counts() == {
        SchemaChange.ADDED: 1,
        SchemaChange.REMOVED: 0,
        SchemaChange.RENAMED: 1,
        SchemaChange.TYPE_CHANGED: 1,
        SchemaChange.NULLABILITY_CHANGED: 0,
        SchemaChange.DOC_CHANGED: 0,
    }


def test_schema_change_values_are_in_documented_order():
    """The change kinds keep the order rows list them in."""
    assert [kind.value for kind in SchemaChange] == [
        "added",
        "removed",
        "renamed",
        "type_changed",
        "nullability_changed",
        "doc_changed",
    ]
