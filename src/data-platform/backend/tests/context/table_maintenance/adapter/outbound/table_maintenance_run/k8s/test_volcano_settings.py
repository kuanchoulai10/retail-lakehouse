"""Test the Volcano queue and priority class a maintenance job goes to."""

from __future__ import annotations

import pytest

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s import VolcanoSettings


@pytest.mark.parametrize(
    ("priority", "queue"),
    [
        ("P0", "table-maintenance-urgent"),
        ("P1", "table-maintenance"),
        ("P2", "table-maintenance"),
        ("P3", "table-maintenance"),
    ],
)
def test_only_p0_goes_to_the_urgent_queue(priority: str, queue: str):
    """P0 takes the urgent queue; P1 to P3 share the normal one."""
    assert VolcanoSettings().queue_for(priority) == queue


@pytest.mark.parametrize("priority", ["P0", "P1", "P2", "P3"])
def test_priority_class_follows_the_priority(priority: str):
    """The priority class is the prefix and the lowercase priority."""
    assert VolcanoSettings().priority_class_for(priority) == f"table-maintenance-{priority.lower()}"


def test_names_are_configurable():
    """The queues and the class prefix come from the settings."""
    settings = VolcanoSettings(queue="q", urgent_queue="uq", priority_class_prefix="pc")

    assert settings.queue_for("P0") == "uq"
    assert settings.queue_for("P2") == "q"
    assert settings.priority_class_for("P1") == "pc-p1"


@pytest.mark.parametrize("priority", ["P9", "p0", "", "P0 "])
def test_an_unknown_priority_is_refused(priority: str):
    """Only exactly P0, P1, P2 and P3 name a queue or a class; anything else is refused, case included."""
    settings = VolcanoSettings()

    with pytest.raises(ValueError, match="priority"):
        settings.queue_for(priority)
    with pytest.raises(ValueError, match="priority"):
        settings.priority_class_for(priority)
