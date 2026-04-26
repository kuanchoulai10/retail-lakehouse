"""Tests for Component enum."""

from __future__ import annotations

from bootstrap.configs.component import Component


def test_component_values():
    """Verify all component values match bootstrap filenames."""
    assert Component.API == "api"
    assert Component.SCHEDULER == "scheduler"
    assert Component.MESSAGING == "messaging"


def test_component_is_str_enum():
    """Verify Component is a StrEnum."""
    assert isinstance(Component.API, str)
    assert Component.API == "api"
