"""Define the InvalidMaintenanceSettings exception."""

from __future__ import annotations


class InvalidMaintenanceSettings(ValueError):
    """Raise when maintenance settings violate an invariant."""
