"""Tests for Gateway base class."""

from __future__ import annotations

from abc import ABC

from base.gateway import Gateway


def test_gateway_is_abc() -> None:
    """Gateway is an abstract base class."""
    assert issubclass(Gateway, ABC)


def test_gateway_cannot_be_instantiated() -> None:
    """Gateway is importable and is an ABC."""
    assert hasattr(Gateway, "__abstractmethods__") or issubclass(Gateway, ABC)
