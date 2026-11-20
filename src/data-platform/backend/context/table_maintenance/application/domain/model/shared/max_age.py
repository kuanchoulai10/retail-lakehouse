"""Define the MAX_AGE constant."""

from __future__ import annotations

from datetime import timedelta

MAX_AGE = timedelta(days=36500)
"""The longest age a retention or orphan cutoff may be: 100 years.

``now - age`` stays a date under it, and a table property over it (Iceberg's ``Long.MAX`` "never by
age") is clamped to it, which keeps "never by age" about right.
"""
