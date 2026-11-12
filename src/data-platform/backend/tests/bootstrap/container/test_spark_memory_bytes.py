"""Test reading a Spark memory setting as bytes."""

from __future__ import annotations

import pytest

from bootstrap.container import spark_memory_bytes

MIB = 1024 * 1024


@pytest.mark.parametrize(
    ("setting", "expected"),
    [
        ("768m", 768 * MIB),
        ("1g", 1024 * MIB),
        ("1536M", 1536 * MIB),
        ("2G", 2048 * MIB),
        ("512k", 512 * 1024),
        ("1t", 1024 * 1024 * MIB),
        ("1024", 1024 * MIB),
    ],
)
def test_reads_spark_memory_settings_as_bytes(setting, expected):
    """A Spark memory setting is read in Spark's units; a bare number means MiB, as Spark reads it."""
    assert spark_memory_bytes(setting) == expected


@pytest.mark.parametrize("setting", ["", "1.5g", "lots", "-1g", "0m"])
def test_rejects_settings_spark_would_not_read(setting):
    """A setting that is not a positive whole amount is rejected at startup."""
    with pytest.raises(ValueError, match="memory"):
        spark_memory_bytes(setting)
