"""Define the DiscoverySettings configuration model."""

from __future__ import annotations

from bootstrap.configs.settings_block import SettingsBlock


class DiscoverySettings(SettingsBlock):
    """How often each scanned catalog is scanned for tables."""

    interval_seconds: int = 600
