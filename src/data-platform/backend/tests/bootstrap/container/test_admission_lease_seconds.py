"""Test the admission lease the worker derives from the attempt deadline."""

from __future__ import annotations

from bootstrap.container import admission_lease_seconds
from tests.bootstrap.container.container_support import sqlite_settings


def test_admission_lease_is_deadline_plus_fifteen_minutes():
    """The lease outlives the configured attempt deadline by 15 minutes."""
    assert admission_lease_seconds(sqlite_settings(maintenance_attempt_deadline_seconds=120)) == 1020


def test_admission_lease_defaults_to_six_hours_and_a_quarter():
    """With the default six hour deadline the lease is 22500 seconds."""
    assert admission_lease_seconds(sqlite_settings()) == 22500
