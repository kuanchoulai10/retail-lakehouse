"""Test the SQL repository of the TableMaintenancePolicyAttachment aggregate."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from context.table_maintenance.adapter.outbound.table_maintenance_policy.sql import (
    TableMaintenancePoliciesSqlRepo,
)
from context.table_maintenance.adapter.outbound.table_maintenance_policy_attachment.sql import (
    TableMaintenancePolicyAttachmentsSqlRepo,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    MaintenancePolicyContent,
    TableMaintenancePolicy,
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy_attachment import (
    PolicyTarget,
    PolicyTargetType,
    TableMaintenancePolicyAttachment,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine

NOW = datetime(2026, 10, 24, tzinfo=UTC)
CATALOG = PolicyTarget(type=PolicyTargetType.CATALOG, path=("prod",))
NAMESPACE = PolicyTarget(type=PolicyTargetType.NAMESPACE, path=("prod", "sales", "eu"))
TABLE = PolicyTarget(type=PolicyTargetType.TABLE, path=("prod", "sales", "orders"), table_uuid="u-1")


@pytest.fixture
def repo(engine: Engine) -> TableMaintenancePolicyAttachmentsSqlRepo:
    """Provide the attachments repository with the policies gold and silver stored."""
    policies = TableMaintenancePoliciesSqlRepo(engine)
    for name in ("gold", "silver"):
        policies.create(
            TableMaintenancePolicy.create(
                TableMaintenancePolicyName(name), MaintenancePolicyContent.platform_default(), NOW
            )
        )
    return TableMaintenancePolicyAttachmentsSqlRepo(engine)


def _attach(target: PolicyTarget, policy: str = "gold") -> TableMaintenancePolicyAttachment:
    return TableMaintenancePolicyAttachment.attach(target, TableMaintenancePolicyName(policy), NOW)


def test_roundtrip_of_each_target_type(repo: TableMaintenancePolicyAttachmentsSqlRepo):
    """Catalog, namespace and table attachments load back equal in every field."""
    for target in (CATALOG, NAMESPACE, TABLE):
        repo.create(_attach(target))
        loaded = repo.get(target.attachment_id())
        assert loaded is not None
        assert loaded.target == target
        assert loaded.policy_name.value == "gold"
        assert loaded.attached_at == NOW


def test_update_replaces_the_policy(repo: TableMaintenancePolicyAttachmentsSqlRepo):
    """Updating an attachment stores its new policy."""
    attachment = _attach(CATALOG)
    repo.create(attachment)
    attachment.replace_policy(TableMaintenancePolicyName("silver"), NOW)
    repo.update(attachment)
    loaded = repo.get(CATALOG.attachment_id())
    assert loaded is not None
    assert loaded.policy_name.value == "silver"


def test_get_many_and_list_for_policy_and_delete(repo: TableMaintenancePolicyAttachmentsSqlRepo):
    """Lookups by ids and by policy see the stored attachments; delete removes one."""
    repo.create(_attach(CATALOG, "gold"))
    repo.create(_attach(NAMESPACE, "silver"))
    found = repo.get_many([NAMESPACE.attachment_id(), TABLE.attachment_id()])
    assert [a.id for a in found] == [NAMESPACE.attachment_id()]
    assert [a.id for a in repo.list_for_policy(TableMaintenancePolicyName("gold"))] == [CATALOG.attachment_id()]
    assert repo.has_attachments_for_policy(TableMaintenancePolicyName("silver"))
    repo.delete(NAMESPACE.attachment_id())
    assert not repo.has_attachments_for_policy(TableMaintenancePolicyName("silver"))
    assert len(repo.list_all()) == 1
