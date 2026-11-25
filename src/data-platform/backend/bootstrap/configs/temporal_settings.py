"""Define the TemporalSettings configuration model."""

from __future__ import annotations

from bootstrap.configs.settings_block import SettingsBlock


class TemporalSettings(SettingsBlock):
    """Temporal frontend address and namespace.

    The task queue is the domain constant ``TASK_QUEUE``, not a setting: workflows,
    schedules and gateways all route by it.
    """

    address: str = "temporal-frontend.temporal.svc.cluster.local:7233"
    namespace: str = "default"
