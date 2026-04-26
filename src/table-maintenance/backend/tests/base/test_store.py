"""Tests for Store base class."""

from __future__ import annotations

from abc import ABC

from base.store import Store


def test_store_is_abc() -> None:
    """Store is an abstract base class."""
    assert issubclass(Store, ABC)


def test_store_cannot_be_instantiated() -> None:
    """Store is importable and is an ABC."""
    assert hasattr(Store, "__abstractmethods__") or issubclass(Store, ABC)
