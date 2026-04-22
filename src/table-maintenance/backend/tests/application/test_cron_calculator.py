"""Tests for cron next-run calculator."""

from datetime import UTC, datetime

import pytest

from application.cron_calculator import next_run_from_cron


def test_next_run_every_hour():
    """Given '0 * * * *' at 10:00, next run is 11:00."""
    base = datetime(2026, 4, 22, 10, 0, tzinfo=UTC)
    result = next_run_from_cron("0 * * * *", base)
    assert result == datetime(2026, 4, 22, 11, 0, tzinfo=UTC)


def test_next_run_daily_at_midnight():
    """Given '0 0 * * *' at 10:30, next run is next day 00:00."""
    base = datetime(2026, 4, 22, 10, 30, tzinfo=UTC)
    result = next_run_from_cron("0 0 * * *", base)
    assert result == datetime(2026, 4, 23, 0, 0, tzinfo=UTC)


def test_next_run_every_5_minutes():
    """Given '*/5 * * * *' at 10:07, next run is 10:10."""
    base = datetime(2026, 4, 22, 10, 7, tzinfo=UTC)
    result = next_run_from_cron("*/5 * * * *", base)
    assert result == datetime(2026, 4, 22, 10, 10, tzinfo=UTC)


def test_invalid_cron_raises_value_error():
    """An invalid cron expression raises ValueError."""
    with pytest.raises(ValueError):
        next_run_from_cron("not-a-cron", datetime(2026, 4, 22, tzinfo=UTC))
