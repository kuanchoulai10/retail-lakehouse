"""Test the priority weights built from the scheduler settings."""

from __future__ import annotations

from bootstrap.configs import PriorityWeightSettings, SchedulerSettings
from bootstrap.container import build_priority_weights
from context.table_maintenance.application.domain.model.compaction_round import PriorityWeights


def test_default_settings_give_the_default_weights():
    """The default settings weigh priorities as the domain's defaults do."""
    assert build_priority_weights(SchedulerSettings()) == PriorityWeights()


def test_every_weight_reaches_its_priority():
    """Each priority's weight comes from its own setting."""
    settings = SchedulerSettings(priority_weights=PriorityWeightSettings(p0=9.0, p1=3.0, p2=0.5))

    assert build_priority_weights(settings) == PriorityWeights(p0=9.0, p1=3.0, p2=0.5)
