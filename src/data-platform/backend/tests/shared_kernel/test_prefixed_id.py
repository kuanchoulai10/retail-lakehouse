"""The shared kernel encodes a UUIDv7 as ``<prefix>-<26 Crockford base32 characters>``."""

from __future__ import annotations

import uuid

import pytest

from shared_kernel import new_prefixed_id, prefixed_id_from_parts, prefixed_id_pattern

TYPEID_SPEC_UUID = uuid.UUID("0188bac7-4afa-78aa-bc3b-bd1eef28d881")
TYPEID_SPEC_SUFFIX = "01h2xcejqtf2nbrexx3vqjhp41"
CROCKFORD = "0123456789abcdefghjkmnpqrstvwxyz"


def _parts_of(value: uuid.UUID) -> tuple[int, int]:
    """Return the unix milliseconds and the 74 random bits (rand_a then rand_b) of a UUIDv7."""
    unix_ms = value.int >> 80
    rand_a = (value.int >> 64) & 0xFFF
    rand_b = value.int & ((1 << 62) - 1)
    return unix_ms, (rand_a << 62) | rand_b


def test_encodes_the_typeid_spec_vector():
    """The TypeID specification's UUID encodes to the specification's suffix."""
    unix_ms, random_bits = _parts_of(TYPEID_SPEC_UUID)

    assert prefixed_id_from_parts("mr", unix_ms, random_bits) == f"mr-{TYPEID_SPEC_SUFFIX}"


def test_ids_sort_by_time():
    """An id with an earlier timestamp sorts before a later one as a string."""
    earlier = prefixed_id_from_parts("mr", 1, (1 << 74) - 1)
    later = prefixed_id_from_parts("mr", 2, 0)

    assert earlier < later


def test_suffix_shape():
    """A new id is the prefix, a dash and 26 characters, and matches its pattern."""
    new_id = new_prefixed_id("mr")

    assert len(new_id) == 29
    assert prefixed_id_pattern("mr").fullmatch(new_id)


def test_same_parts_same_id():
    """The same parts always give the same id."""
    assert prefixed_id_from_parts("mr", 1_700_000_000_000, 12345) == prefixed_id_from_parts(
        "mr", 1_700_000_000_000, 12345
    )


def test_different_random_bits_differ():
    """Different random bits give a different id."""
    assert prefixed_id_from_parts("mr", 1, 1) != prefixed_id_from_parts("mr", 1, 2)


def test_only_the_low_74_random_bits_are_used():
    """Bits above the 74th are ignored, so they cannot disturb the version or variant."""
    assert prefixed_id_from_parts("mr", 1, 5) == prefixed_id_from_parts("mr", 1, 5 | (0xFF << 74))


def _decode(suffix: str) -> int:
    """Decode a 26-character suffix back to the 128-bit integer, independently of the encoder."""
    value = 0
    for character in suffix:
        value = (value << 5) | CROCKFORD.index(character)
    return value


def test_the_id_is_a_uuid_v7_with_its_timestamp():
    """Decoding the suffix gives version 7, variant 10, the given milliseconds and the given random bits."""
    unix_ms = 1_700_000_000_123
    random_bits = (0xABC << 62) | 0x123456789ABCDEF

    decoded = _decode(prefixed_id_from_parts("mr", unix_ms, random_bits).removeprefix("mr-"))

    assert decoded >> 80 == unix_ms
    assert (decoded >> 76) & 0xF == 7
    assert (decoded >> 62) & 0b11 == 0b10
    assert _parts_of(uuid.UUID(int=decoded)) == (unix_ms, random_bits)


def test_a_new_id_is_a_uuid_v7():
    """An id from ``new_prefixed_id`` decodes to a version 7, variant 10 UUID."""
    decoded = _decode(new_prefixed_id("mr").removeprefix("mr-"))

    assert uuid.UUID(int=decoded).version == 7
    assert (decoded >> 62) & 0b11 == 0b10


def test_the_pattern_rejects_a_wrong_prefix_or_alphabet():
    """The pattern accepts its own prefix only, and only characters of the alphabet."""
    pattern = prefixed_id_pattern("mr")

    assert pattern.fullmatch("mr-" + TYPEID_SPEC_SUFFIX)
    assert not pattern.fullmatch("dp-" + TYPEID_SPEC_SUFFIX)
    assert not pattern.fullmatch("mr-8" + TYPEID_SPEC_SUFFIX[1:])
    assert not pattern.fullmatch("mr-" + "u" + TYPEID_SPEC_SUFFIX[1:])
    assert not pattern.fullmatch("mr-" + TYPEID_SPEC_SUFFIX.upper())
    assert not pattern.fullmatch("mr-" + TYPEID_SPEC_SUFFIX[:-1])


@pytest.mark.parametrize("prefix", ["MR", "m", "mr-", "abcdefghi", "m1", ""])
def test_refuses_bad_prefix(prefix: str):
    """A prefix must be 2 to 8 lowercase letters."""
    with pytest.raises(ValueError, match="prefix"):
        prefixed_id_from_parts(prefix, 1, 1)
    with pytest.raises(ValueError, match="prefix"):
        new_prefixed_id(prefix)
    with pytest.raises(ValueError, match="prefix"):
        prefixed_id_pattern(prefix)


@pytest.mark.parametrize("unix_ms", [-1, 1 << 48], ids=["negative", "past 48 bits"])
def test_refuses_milliseconds_outside_48_bits(unix_ms: int):
    """The UUIDv7 time field holds 48 bits, so a negative or larger value is refused."""
    with pytest.raises(ValueError, match="unix_ms must fit in 48 bits"):
        prefixed_id_from_parts("mr", unix_ms, 1)
