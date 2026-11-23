"""Test ReadOnlyMapping: the immutable mapping a domain model field holds instead of a dict."""

from __future__ import annotations

import copy
import json
import pickle
from collections.abc import Mapping
from typing import Any, cast

import pytest

from base import Entity, EntityId, InvariantViolation, ReadOnlyMapping, ValueObject


class _Holder(ValueObject):
    """Test stub: a value object with a typed mapping."""

    counts: ReadOnlyMapping[str, int]


class _Bag(ValueObject):
    """Test stub: a value object with a mapping of any JSON value."""

    data: ReadOnlyMapping[str, Any]


class _BoxId(EntityId):
    """Test stub for EntityId."""


class _Box(Entity[_BoxId]):
    """Test stub: an entity with a typed mapping it may replace."""

    counts: ReadOnlyMapping[str, int]


def _box() -> _Box:
    return _Box(id=_BoxId("1"), counts={"a": 1})


def _frozen(counts: dict[str, Any]) -> Mapping[str, Any]:
    """Return ``counts`` as the field holds it."""
    return _Bag(data=counts).data


def _refused(edit: Any) -> None:  # noqa: ANN401
    with pytest.raises(TypeError, match="^ReadOnlyMapping is read-only: assign a new mapping to the field instead$"):
        edit()


def test_a_field_accepts_a_dict_and_holds_a_read_only_mapping() -> None:
    """A dict given to the field is kept as a read-only mapping, not as the dict itself."""
    given = {"a": 1}
    counts = _Holder(counts=given).counts
    assert isinstance(counts, Mapping)
    assert counts is not given
    assert repr(counts) == "ReadOnlyMapping({'a': 1})"


def test_item_assignment_deletion_and_editing_methods_are_refused() -> None:
    """The mapping cannot be edited in place by any route a dict offers."""
    counts = cast("Any", _Holder(counts={"a": 1}).counts)
    _refused(lambda: counts.__setitem__("a", 2))
    _refused(lambda: counts.__delitem__("a"))
    _refused(lambda: counts.update(b=2))
    _refused(lambda: counts.pop("a"))
    _refused(counts.popitem)
    _refused(counts.clear)
    _refused(lambda: counts.setdefault("b", 2))
    _refused(lambda: counts.__ior__({"b": 2}))
    assert counts == {"a": 1}


@pytest.mark.parametrize("counts", [{"a": "1"}, {1: 1}])
def test_keys_and_values_are_validated_strictly(counts: dict[Any, Any]) -> None:
    """A key or value of the wrong type is refused, with no coercion."""
    with pytest.raises(InvariantViolation):
        _Holder(counts=counts)


def test_a_read_only_mapping_is_accepted_as_is() -> None:
    """A ReadOnlyMapping given to the field is accepted, and its values are still checked."""
    assert _Holder(counts=_frozen({"a": 1})).counts == {"a": 1}
    with pytest.raises(InvariantViolation):
        _Holder(counts=_frozen({"a": "1"}))


def test_reassigning_the_field_holds_a_read_only_mapping_again() -> None:
    """An entity that replaces the mapping with a dict holds a ReadOnlyMapping again."""
    box = _box()
    box.counts = {**box.counts, "b": 2}
    assert box.counts == {"a": 1, "b": 2}
    _refused(lambda: box.counts.__setitem__("c", 3))  # ty: ignore[unresolved-attribute]


def test_nested_dicts_and_lists_are_frozen() -> None:
    """Dicts and lists inside the values are frozen too, so nothing inside can be edited."""
    data = _Bag(data={"x": {"y": [1, {"z": 2}]}}).data
    assert data["x"]["y"] == (1, {"z": 2})
    _refused(lambda: data["x"].__setitem__("k", 1))
    _refused(lambda: data["x"]["y"][1].__setitem__("k", 1))


def test_dumps_give_plain_dicts_and_lists() -> None:
    """Dumping gives plain dicts and lists, nested too, and the JSON round-trips."""
    bag = _Bag(data={"x": {"y": [1, {"z": 2}]}})
    dumped = bag.model_dump()
    assert dumped == {"data": {"x": {"y": [1, {"z": 2}]}}}
    assert type(dumped["data"]) is dict
    assert type(dumped["data"]["x"]) is dict
    assert type(dumped["data"]["x"]["y"]) is list
    assert type(dumped["data"]["x"]["y"][1]) is dict
    text = bag.model_dump_json()
    assert text == '{"data":{"x":{"y":[1,{"z":2}]}}}'
    assert _Bag.model_validate_json(text) == bag


def test_json_encodes_like_a_dict() -> None:
    """A copy an adapter makes with ``dict(...)`` still encodes as JSON, nested values too."""
    data = _Bag(data={"x": {"y": [1, {"z": 2}]}}).data
    assert json.dumps(dict(data)) == '{"x": {"y": [1, {"z": 2}]}}'


def test_equality_with_a_dict_and_between_models() -> None:
    """A ReadOnlyMapping equals any mapping with the same items, and models compare by content."""
    assert _frozen({"a": 1}) == {"a": 1}
    assert _frozen({"a": 1}) != {"a": 2}
    assert _frozen({"a": 1}) != [("a", 1)]
    assert _Holder(counts={"a": 1}) == _Holder(counts=_frozen({"a": 1}))


def test_hashable_when_its_values_are() -> None:
    """Equal mappings hash alike, so a value object holding one stays hashable."""
    assert hash(_frozen({"a": {"b": [1]}})) == hash(_frozen({"a": {"b": [1]}}))
    assert hash(_Holder(counts={"a": 1})) == hash(_Holder(counts={"a": 1}))
    assert hash(_Holder(counts={"a": 1})) != hash(_Holder(counts={"a": 2}))


@pytest.mark.parametrize(
    "clone",
    [copy.copy, copy.deepcopy, lambda m: pickle.loads(pickle.dumps(m))],  # noqa: S301
    ids=["copy", "deepcopy", "pickle"],
)
def test_copy_deepcopy_and_pickle_keep_it_read_only(clone: Any) -> None:  # noqa: ANN401
    """A copy, a deep copy and an unpickled mapping are equal and still read-only."""
    cloned = clone(_frozen({"a": {"b": 1}}))
    assert cloned == {"a": {"b": 1}}
    _refused(lambda: cloned.__setitem__("c", 1))
    _refused(lambda: cloned["a"].__setitem__("c", 1))


def test_a_deep_model_copy_keeps_the_mapping() -> None:
    """``model_copy(deep=True)``, which in-memory test stores use, keeps the mapping."""
    counts = _box().model_copy(deep=True).counts
    assert counts == {"a": 1}
    _refused(lambda: counts.__setitem__("b", 2))  # ty: ignore[unresolved-attribute]
