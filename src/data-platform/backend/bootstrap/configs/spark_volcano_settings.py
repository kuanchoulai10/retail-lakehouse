"""Define the SparkVolcanoSettings configuration model."""

from __future__ import annotations

from bootstrap.configs.settings_block import SettingsBlock


class SparkVolcanoSettings(SettingsBlock):
    """Volcano queues and priority classes the maintenance SparkApplications are scheduled in.

    A P0 job goes to ``urgent_queue``, every other priority to ``queue``; the priority class
    is ``priority_class_prefix``, a dash and the lowercase priority. The Helm chart creates them.
    """

    queue: str = "table-maintenance"
    urgent_queue: str = "table-maintenance-urgent"
    priority_class_prefix: str = "table-maintenance"
