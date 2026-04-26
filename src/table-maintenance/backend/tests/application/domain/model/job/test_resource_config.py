"""Tests for ResourceConfig value object."""

import pytest

from application.domain.model.job import ResourceConfig


def test_default_values():
    """Verify ResourceConfig provides sensible defaults."""
    config = ResourceConfig()
    assert config.driver_memory == "512m"
    assert config.executor_memory == "1g"
    assert config.executor_instances == 1


def test_stores_custom_values():
    """Verify custom values are stored correctly."""
    config = ResourceConfig(
        driver_memory="2g",
        executor_memory="4g",
        executor_instances=3,
    )
    assert config.driver_memory == "2g"
    assert config.executor_memory == "4g"
    assert config.executor_instances == 3


def test_equality_by_value():
    """Verify two ResourceConfigs with the same fields are equal."""
    a = ResourceConfig(driver_memory="1g", executor_memory="2g", executor_instances=2)
    b = ResourceConfig(driver_memory="1g", executor_memory="2g", executor_instances=2)
    assert a == b


def test_inequality():
    """Verify two ResourceConfigs with different fields are not equal."""
    a = ResourceConfig(driver_memory="1g", executor_memory="2g", executor_instances=2)
    b = ResourceConfig(driver_memory="2g", executor_memory="2g", executor_instances=2)
    assert a != b


def test_is_frozen():
    """Verify ResourceConfig is immutable."""
    config = ResourceConfig()
    with pytest.raises(AttributeError):
        config.driver_memory = "2g"  # type: ignore[misc]  # ty: ignore[invalid-assignment]
