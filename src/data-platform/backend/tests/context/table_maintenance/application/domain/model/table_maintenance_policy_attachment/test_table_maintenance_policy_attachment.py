"""Test the table maintenance policy attachment aggregate."""

from __future__ import annotations

from datetime import UTC, datetime

from context.table_maintenance.application.domain.model.shared import (
    PolicyTarget,
    PolicyTargetType,
    TableMaintenancePolicyId,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy_attachment import (
    TableMaintenancePolicyAttachment,
)
from shared_kernel import prefixed_id_pattern

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_attachment_id_has_the_pa_prefix():
    """Attaching mints a random pa- id, never one derived from the target."""
    target = PolicyTarget(type=PolicyTargetType.CATALOG, path=("c",))
    gold = TableMaintenancePolicyId.new()
    first = TableMaintenancePolicyAttachment.attach(target, gold, NOW)
    second = TableMaintenancePolicyAttachment.attach(target, gold, NOW)
    assert prefixed_id_pattern("pa").fullmatch(first.id.value)
    assert first.id != second.id


def test_attach_and_replace_policy():
    """An attachment records its policy by id and moves to another, keeping its own id."""
    target = PolicyTarget(type=PolicyTargetType.CATALOG, path=("c",))
    gold, silver = TableMaintenancePolicyId.new(), TableMaintenancePolicyId.new()
    attachment = TableMaintenancePolicyAttachment.attach(target, gold, NOW)
    assert attachment.policy_id == gold
    attached_id = attachment.id
    later = datetime(2026, 2, 1, tzinfo=UTC)
    attachment.replace_policy(silver, later)
    assert attachment.policy_id == silver
    assert attachment.attached_at == later
    assert attachment.id == attached_id
