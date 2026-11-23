"""Tests for the Pydantic EntityId base type."""

from __future__ import annotations

import uuid
from typing import ClassVar

import pytest

from base import EntityId, InvariantViolation, ValueObject

RUN_ID = "mr-01h2xcejqtf2nbrexx3vqjhp41"
TYPEID_SPEC_UUID = uuid.UUID("0188bac7-4afa-78aa-bc3b-bd1eef28d881")
TYPEID_SPEC_SUFFIX = "01h2xcejqtf2nbrexx3vqjhp41"
CROCKFORD = "0123456789abcdefghjkmnpqrstvwxyz"


class _Id(EntityId):
    """Test stub for EntityId."""


class _OtherId(EntityId):
    """A second EntityId kind with the same raw values."""


class _RunId(EntityId):
    """A prefixed EntityId kind."""

    PREFIX: ClassVar[str | None] = "mr"


class _Holder(ValueObject):
    """A value object holding a prefixed id."""

    run_id: _RunId


class _Pair(ValueObject):
    """A two-field value object built by keyword."""

    name: str
    count: int


def test_positional_construction_type_checks() -> None:
    """An id is built positionally and a value object by keyword, and both type-check."""
    identifier = _Id("a")
    pair = _Pair(name="n", count=1)
    assert identifier.value == "a"
    assert pair.count == 1


def test_value_returns_the_raw_string() -> None:
    """``value`` is the wrapped string."""
    assert _Id("a").value == "a"


def test_str_returns_the_value() -> None:
    """``str()`` is the raw identifier."""
    assert str(_Id("a")) == "a"


def test_same_kind_same_value_is_equal() -> None:
    """Two ids of one kind with one value are equal."""
    assert _Id("a") == _Id("a")


def test_different_value_is_not_equal() -> None:
    """Two ids of one kind with different values differ."""
    assert _Id("a") != _Id("b")


def test_different_kind_same_value_is_not_equal() -> None:
    """Ids of different kinds never compare equal."""
    assert _Id("a") != _OtherId("a")


def test_is_hashable() -> None:
    """Equal ids collapse in a set."""
    assert {_Id("a"), _Id("a")} == {_Id("a")}


def test_is_frozen() -> None:
    """An id cannot be reassigned."""
    identifier = _Id("a")
    with pytest.raises(AttributeError, match="is immutable"):
        identifier.root = "b"


def test_strict_rejects_a_non_string() -> None:
    """Strict mode rejects an int where a string is expected."""
    with pytest.raises(InvariantViolation):
        _Id.model_validate(1)


def test_third_level_subclass_is_rejected() -> None:
    """A concrete id extends EntityId directly."""
    with pytest.raises(TypeError, match="max inheritance depth"):

        class _Deeper(_Id):
            pass


@pytest.mark.parametrize(
    "build",
    [
        _RunId,
        _RunId.model_validate,
        lambda value: _RunId.model_validate_json(f'"{value}"'),
    ],
    ids=["positional", "model_validate", "model_validate_json"],
)
def test_prefixed_id_refuses_a_uuid(build) -> None:
    """Every way of building a prefixed id refuses a bare UUID, naming the class and the expected shape."""
    with pytest.raises(InvariantViolation, match=r"^_RunId must look like mr-<26 base32 characters>$"):
        build(str(uuid.uuid4()))


@pytest.mark.parametrize(
    "value",
    [
        "dp-01h2xcejqtf2nbrexx3vqjhp41",
        RUN_ID + "\n",
        RUN_ID.upper(),
        "mr-81h2xcejqtf2nbrexx3vqjhp41",
        RUN_ID[:-1],
        RUN_ID[:-1] + "u",
        "",
    ],
    ids=[
        "other prefix",
        "trailing newline",
        "upper case",
        "first character above 7",
        "short",
        "letter outside the alphabet",
        "empty",
    ],
)
def test_prefixed_id_refuses_any_other_shape(value: str) -> None:
    """A prefixed id refuses a value of another prefix or of the wrong suffix."""
    with pytest.raises(InvariantViolation, match="_RunId must look like mr-"):
        _RunId(value)


def test_prefixed_id_accepts_its_shape() -> None:
    """A value of the declared prefix and a valid suffix is accepted on every path."""
    assert _RunId(RUN_ID).value == RUN_ID
    assert _RunId.model_validate(RUN_ID) == _RunId(RUN_ID)
    assert _RunId.model_validate_json(f'"{RUN_ID}"') == _RunId(RUN_ID)


def test_prefixed_id_nested_in_a_value_object_is_checked() -> None:
    """A wrong id inside a value object read from primitives is refused too."""
    with pytest.raises(InvariantViolation, match="must look like mr-"):
        _Holder.from_primitives({"run_id": str(uuid.uuid4())})


def test_prefix_does_not_change_the_wire_form() -> None:
    """``PREFIX`` is not a field: the id dumps, serializes and prints as its bare string."""
    identifier = _RunId(RUN_ID)

    assert identifier.model_dump() == RUN_ID
    assert identifier.model_dump_json() == f'"{RUN_ID}"'
    assert str(identifier) == RUN_ID
    assert set(_RunId.model_fields) == {"root"}


def test_new_mints_a_valid_id() -> None:
    """``new()`` returns an id of the class, matching the prefix pattern, a fresh one each call."""
    minted = _RunId.new()

    assert type(minted) is _RunId
    assert minted.value.startswith("mr-")
    assert len(minted.suffix) == 26
    assert _RunId.new() != minted


def test_unprefixed_id_accepts_any_string() -> None:
    """An id kind without ``PREFIX`` accepts any string, including a UUID and the empty string."""
    assert _Id.PREFIX is None
    assert _Id(str(uuid.uuid4())).value
    assert _Id("").value == ""
    assert _Id(RUN_ID).value == RUN_ID


def test_new_without_prefix_is_type_error() -> None:
    """``new()`` on an id kind without ``PREFIX`` raises ``TypeError`` naming the class."""
    with pytest.raises(TypeError, match="_Id has no PREFIX"):
        _Id.new()


def test_an_invalid_prefix_is_refused_when_the_class_is_defined() -> None:
    """A ``PREFIX`` that is not 2 to 8 lowercase letters fails at class definition."""
    for prefix in ("MR", "m", "mr-", "abcdefghi", "m1", ""):
        with pytest.raises(ValueError, match="prefix must be 2 to 8 lowercase letters"):

            class _BadId(EntityId):
                PREFIX: ClassVar[str | None] = prefix


def test_a_kind_defined_without_a_prefix_accepts_any_value() -> None:
    """A kind without ``PREFIX`` checks no shape, even when defined after the others.

    The class is defined here, not at module level, so its definition runs while the test runs.
    """

    class _FreeId(EntityId):
        pass

    assert _FreeId("anything at all").value == "anything at all"


def test_suffix_is_the_part_after_the_prefix() -> None:
    """A prefixed id's ``suffix`` is the 26 characters after ``<PREFIX>-``."""
    assert _RunId(RUN_ID).suffix == "01h2xcejqtf2nbrexx3vqjhp41"


def test_suffix_needs_a_prefix() -> None:
    """An id kind without ``PREFIX`` has no suffix and raises ``TypeError`` naming the class."""
    with pytest.raises(TypeError, match="_Id has no PREFIX"):
        _ = _Id("mr-01h2xcejqtf2nbrexx3vqjhp41").suffix


def _uuid7(unix_ms: int, random_bits: int) -> uuid.UUID:
    """Build a UUIDv7 from its milliseconds and 74 random bits (12 of ``rand_a`` then 62 of ``rand_b``)."""
    rand_a, rand_b = random_bits >> 62, random_bits & ((1 << 62) - 1)
    return uuid.UUID(int=(unix_ms << 80) | (0x7 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b)


def _decode(suffix: str) -> int:
    """Decode a 26-character suffix back to the 128-bit integer, independently of the encoder."""
    value = 0
    for character in suffix:
        value = (value << 5) | CROCKFORD.index(character)
    return value


def test_new_encodes_the_typeid_spec_vector(monkeypatch: pytest.MonkeyPatch) -> None:
    """The TypeID specification's UUID becomes the specification's suffix."""
    monkeypatch.setattr(uuid, "uuid7", lambda: TYPEID_SPEC_UUID)

    assert _RunId.new().value == f"mr-{TYPEID_SPEC_SUFFIX}"


def test_new_ids_sort_by_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """An id from an earlier millisecond sorts before a later one as a string, whatever the random bits."""
    uuids = iter([_uuid7(1, (1 << 74) - 1), _uuid7(2, 0)])
    monkeypatch.setattr(uuid, "uuid7", lambda: next(uuids))

    earlier, later = _RunId.new(), _RunId.new()

    assert earlier.value < later.value


def test_the_suffix_of_a_new_id_decodes_to_its_uuid(monkeypatch: pytest.MonkeyPatch) -> None:
    """Decoding the suffix gives back the UUIDv7 the id was made from, timestamp, version and variant included."""
    made_from = _uuid7(1_700_000_000_123, (0xABC << 62) | 0x123456789ABCDEF)
    monkeypatch.setattr(uuid, "uuid7", lambda: made_from)

    decoded = _decode(_RunId.new().suffix)

    assert decoded == made_from.int
    assert decoded >> 80 == 1_700_000_000_123
    assert uuid.UUID(int=decoded).version == 7


def test_a_new_id_is_a_uuid_v7() -> None:
    """An id from ``new()`` decodes to a version 7, variant 10 UUID."""
    decoded = _decode(_RunId.new().suffix)

    assert uuid.UUID(int=decoded).version == 7
    assert (decoded >> 62) & 0b11 == 0b10


@pytest.mark.parametrize(
    ("text", "shaped"),
    [
        ("mr-" + TYPEID_SPEC_SUFFIX, True),
        ("abcdefgh-" + TYPEID_SPEC_SUFFIX, True),
        ("m-" + TYPEID_SPEC_SUFFIX, False),
        ("abcdefghi-" + TYPEID_SPEC_SUFFIX, False),
        ("MR-" + TYPEID_SPEC_SUFFIX, False),
        ("mr-8" + TYPEID_SPEC_SUFFIX[1:], False),
        ("mr-" + TYPEID_SPEC_SUFFIX[:-1], False),
        ("mr-nightly", False),
        ("mr-" + TYPEID_SPEC_SUFFIX + "x", False),
        ("policy mr-" + TYPEID_SPEC_SUFFIX, False),
    ],
)
def test_is_shaped_like_an_id_of_any_prefix(text: str, shaped: bool) -> None:  # noqa: FBT001
    """Text is shaped like an id when it is a prefix of 2 to 8 lowercase letters, a dash and a valid suffix."""
    assert EntityId.is_shaped_like_an_id(text) is shaped
