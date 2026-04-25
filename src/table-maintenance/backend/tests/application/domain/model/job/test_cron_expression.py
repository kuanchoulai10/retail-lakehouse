"""Tests for CronExpression value object."""

from datetime import UTC, datetime

import pytest

from core.application.domain.model.job import CronExpression


def test_stores_expression():
    """Verify that the expression is stored correctly."""
    cron = CronExpression(expression="0 * * * *")
    assert cron.expression == "0 * * * *"


def test_invalid_cron_raises_on_construction():
    """Verify that an invalid cron expression raises ValueError."""
    with pytest.raises(ValueError, match="Invalid cron expression"):
        CronExpression(expression="not-a-cron")


def test_next_run_after():
    """Verify next_run_after returns the correct next time."""
    cron = CronExpression(expression="0 * * * *")
    base = datetime(2026, 4, 22, 10, 0, tzinfo=UTC)
    result = cron.next_run_after(base)
    assert result == datetime(2026, 4, 22, 11, 0, tzinfo=UTC)


def test_next_run_daily():
    """Verify next_run_after works for daily cron."""
    cron = CronExpression(expression="0 0 * * *")
    base = datetime(2026, 4, 22, 10, 30, tzinfo=UTC)
    result = cron.next_run_after(base)
    assert result == datetime(2026, 4, 23, 0, 0, tzinfo=UTC)


def test_equality_by_value():
    """Verify two CronExpressions with the same expression are equal."""
    a = CronExpression(expression="0 * * * *")
    b = CronExpression(expression="0 * * * *")
    assert a == b


def test_inequality():
    """Verify two CronExpressions with different expressions are not equal."""
    a = CronExpression(expression="0 * * * *")
    b = CronExpression(expression="*/5 * * * *")
    assert a != b


def test_is_frozen():
    """Verify CronExpression is immutable."""
    cron = CronExpression(expression="0 * * * *")
    with pytest.raises(AttributeError):
        cron.expression = "*/5 * * * *"  # type: ignore[misc]  # ty: ignore[invalid-assignment]
