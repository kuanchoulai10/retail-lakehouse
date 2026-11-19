"""Build a prefixed id from the parts of a UUIDv7."""

from __future__ import annotations

from shared_kernel._checked_prefix import checked_prefix
from shared_kernel._crockford import encode_128_bits

_RANDOM_BITS = 74
_RAND_B_BITS = 62
_VERSION_7 = 0x7


def prefixed_id_from_parts(prefix: str, unix_ms: int, random_bits: int) -> str:
    """Return ``<prefix>-<26 characters>``, the suffix being a UUIDv7 in Crockford base32.

    The UUIDv7 holds 48 bits of ``unix_ms``, version 7, 12 random bits (``rand_a``), variant ``10`` and 62 random
    bits (``rand_b``). The 74 random bits come from the low 74 bits of ``random_bits``; higher bits are ignored.
    """
    prefix = checked_prefix(prefix)
    if not 0 <= unix_ms < 1 << 48:
        raise ValueError("unix_ms must fit in 48 bits")
    random_bits &= (1 << _RANDOM_BITS) - 1
    rand_a = random_bits >> _RAND_B_BITS
    rand_b = random_bits & ((1 << _RAND_B_BITS) - 1)
    value = (unix_ms << 80) | (_VERSION_7 << 76) | (rand_a << 64) | (0b10 << _RAND_B_BITS) | rand_b
    return f"{prefix}-{encode_128_bits(value)}"
