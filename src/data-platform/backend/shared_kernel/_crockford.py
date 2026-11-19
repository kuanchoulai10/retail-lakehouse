"""Crockford base32 encoding of a 128-bit integer, as the TypeID specification writes it."""

from __future__ import annotations

_ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"


def encode_128_bits(value: int) -> str:
    """Encode a 128-bit integer as 26 lowercase Crockford base32 characters, big-endian.

    The 130 bits of 26 characters hold the 128 bits with two leading zero bits, so the first character is 0 to 7.
    """
    if not 0 <= value < 1 << 128:
        raise ValueError("value must fit in 128 bits")
    return "".join(_ALPHABET[(value >> shift) & 0b11111] for shift in range(125, -1, -5))
