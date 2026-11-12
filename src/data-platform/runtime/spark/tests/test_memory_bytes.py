from __future__ import annotations

import pytest

from memory_bytes import memory_bytes

MIB = 1024 * 1024


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("768m", 768 * MIB),
        ("1g", 1024 * MIB),
        ("1536m", 1536 * MIB),
        ("2G", 2048 * MIB),
        ("512", 512 * MIB),
        ("1024k", MIB),
        ("1t", 1024 * 1024 * MIB),
        ("100b", 100),
    ],
)
def test_memory_bytes_parses_spark_sizes(value, expected):
    assert memory_bytes(value) == expected


def test_memory_bytes_refuses_what_is_not_a_size():
    with pytest.raises(ValueError, match="memory size"):
        memory_bytes("lots")
