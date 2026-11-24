"""Test unique_suffix, which keeps one run's names apart from another's."""

from __future__ import annotations

import re

from e2e.support import unique_suffix


def test_is_eight_lowercase_hex_characters():
    """The suffix fits Iceberg, Polaris and Kubernetes names alike."""
    assert re.fullmatch(r"[0-9a-f]{8}", unique_suffix())


def test_two_suffixes_differ():
    """Two runs get two suffixes."""
    assert unique_suffix() != unique_suffix()
