"""Test the repositories of the TableDiscoveryPolicyAttachment aggregate, the SQL one and the in-memory fake alike."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, event

from context.table_maintenance.adapter.outbound.shared.sql import create_schema
from context.table_maintenance.adapter.outbound.table_discovery_policy.sql import (
    TableDiscoveryPoliciesSqlRepo,
)
from context.table_maintenance.adapter.outbound.table_discovery_policy_attachment.sql import (
    TableDiscoveryPolicyAttachmentsSqlRepo,
)
from context.table_maintenance.application.domain.model.shared import PolicyTarget, PolicyTargetType
from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DiscoveryPolicyContent,
    TableDiscoveryPolicy,
    TableDiscoveryPolicyId,
    TableDiscoveryPolicyName,
)
from context.table_maintenance.application.domain.model.table_discovery_policy_attachment import (
    TableDiscoveryPolicyAttachment,
)
from context.table_maintenance.application.exceptions import ConflictError
from tests.context.table_maintenance.fakes.in_memory_table_discovery_policy_attachments_repo import (
    InMemoryTableDiscoveryPolicyAttachmentsRepo,
)
from tests.context.table_maintenance.numbered_id import numbered_id

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy import Engine

    from context.table_maintenance.application.port.outbound.table_discovery_policy_attachment import (
        TableDiscoveryPolicyAttachmentsRepo,
    )

NOW = datetime(2026, 11, 1, tzinfo=UTC)
CATALOG = PolicyTarget(type=PolicyTargetType.CATALOG, path=("prod",))
NAMESPACE = PolicyTarget(type=PolicyTargetType.NAMESPACE, path=("prod", "sales", "eu"))
TABLE = PolicyTarget(type=PolicyTargetType.TABLE, path=("prod", "sales", "orders"), table_uuid="u-1")
OTHER_CATALOG = PolicyTarget(type=PolicyTargetType.CATALOG, path=("dev",))
OTHER_NAMESPACE = PolicyTarget(type=PolicyTargetType.NAMESPACE, path=("dev", "sales"))
POLICY_IDS = {
    "manage-sales": TableDiscoveryPolicyId(numbered_id("dp", 1)),
    "manage-all": TableDiscoveryPolicyId(numbered_id("dp", 2)),
}


def _store_policies(engine: Engine) -> None:
    policies = TableDiscoveryPoliciesSqlRepo(engine)
    for name, policy_id in POLICY_IDS.items():
        policies.create(
            TableDiscoveryPolicy(
                id=policy_id,
                name=TableDiscoveryPolicyName(value=name),
                content=DiscoveryPolicyContent.from_primitives({"no_match_outcome": "manage", "rules": []}),
                version=1,
                created_at=NOW,
                updated_at=NOW,
            )
        )


@pytest.fixture(params=["sql", "memory"])
def attachments(request: pytest.FixtureRequest, engine: Engine) -> TableDiscoveryPolicyAttachmentsRepo:
    """Provide each attachments repository implementation; the SQL one with both policies stored."""
    if request.param == "sql":
        _store_policies(engine)
        return TableDiscoveryPolicyAttachmentsSqlRepo(engine)
    return InMemoryTableDiscoveryPolicyAttachmentsRepo()


def _attach(target: PolicyTarget, policy: str = "manage-sales") -> TableDiscoveryPolicyAttachment:
    return TableDiscoveryPolicyAttachment.attach(target, POLICY_IDS[policy], NOW)


def test_each_target_type_round_trips(attachments: TableDiscoveryPolicyAttachmentsRepo):
    """Catalog, namespace and table attachments load back equal in every field, by id and by target."""
    for target in (CATALOG, NAMESPACE, TABLE):
        attachment = _attach(target)
        attachments.create(attachment)

        loaded = attachments.get(attachment.id)

        assert loaded is not None
        assert (loaded.id, loaded.target, loaded.policy_id, loaded.attached_at) == (
            attachment.id,
            target,
            POLICY_IDS["manage-sales"],
            NOW,
        )
        assert loaded.attached_at.tzinfo is not None
        assert attachments.get_by_target(target) == loaded


def test_a_table_target_round_trips_its_uuid(attachments: TableDiscoveryPolicyAttachmentsRepo):
    """A table attachment keeps its uuid, and is found by it under whatever path the table now has."""
    attachment = _attach(TABLE)
    attachments.create(attachment)

    loaded = attachments.get(attachment.id)
    renamed = PolicyTarget(type=PolicyTargetType.TABLE, path=("prod", "archive", "orders_old"), table_uuid="u-1")

    assert loaded is not None
    assert loaded.target.table_uuid == "u-1"
    assert loaded.target.path == ("prod", "sales", "orders")
    found = attachments.get_by_target(renamed)
    assert found is not None
    assert found.id == attachment.id


def test_one_attachment_per_target(attachments: TableDiscoveryPolicyAttachmentsRepo):
    """A second create on a target that already has one is a ConflictError, whatever its id, and the first stays."""
    first, second = _attach(NAMESPACE, "manage-sales"), _attach(NAMESPACE, "manage-all")
    assert first.id != second.id
    attachments.create(first)

    with pytest.raises(ConflictError):
        attachments.create(second)

    assert [a.id for a in attachments.list_all()] == [first.id]


def test_list_in_catalog_returns_only_that_catalog(attachments: TableDiscoveryPolicyAttachmentsRepo):
    """The catalog's own, namespace and table attachments are listed, and none of another catalog."""
    in_prod = [_attach(CATALOG), _attach(NAMESPACE), _attach(TABLE)]
    for attachment in (*in_prod, _attach(OTHER_CATALOG), _attach(OTHER_NAMESPACE)):
        attachments.create(attachment)

    listed = attachments.list_in_catalog("prod")

    assert sorted(a.id.value for a in listed) == sorted(a.id.value for a in in_prod)
    assert attachments.list_in_catalog("missing") == []


def test_update_replaces_the_policy_and_keeps_the_id(attachments: TableDiscoveryPolicyAttachmentsRepo):
    """Updating an attachment stores its new policy and time under the same id."""
    attachment = _attach(CATALOG)
    attachments.create(attachment)
    attachment.replace_policy(POLICY_IDS["manage-all"], NOW + timedelta(hours=1))

    attachments.update(attachment)

    loaded = attachments.get_by_target(CATALOG)
    assert loaded is not None
    assert (loaded.id, loaded.policy_id, loaded.attached_at) == (
        attachment.id,
        POLICY_IDS["manage-all"],
        NOW + timedelta(hours=1),
    )


def test_update_of_an_unknown_attachment_raises_lookup_error(attachments: TableDiscoveryPolicyAttachmentsRepo):
    """Updating an attachment that was never stored is a LookupError."""
    with pytest.raises(LookupError):
        attachments.update(_attach(CATALOG))


def test_list_for_policy_and_has_attachments_and_delete(attachments: TableDiscoveryPolicyAttachmentsRepo):
    """Lookups by policy see the stored attachments; delete removes one, and a second delete is a no-op."""
    catalog, namespace = _attach(CATALOG, "manage-sales"), _attach(NAMESPACE, "manage-all")
    attachments.create(catalog)
    attachments.create(namespace)

    assert [a.id for a in attachments.list_for_policy(POLICY_IDS["manage-sales"])] == [catalog.id]
    assert attachments.has_attachments_for_policy(POLICY_IDS["manage-all"])

    attachments.delete(namespace.id)
    attachments.delete(namespace.id)

    assert not attachments.has_attachments_for_policy(POLICY_IDS["manage-all"])
    assert attachments.get(namespace.id) is None
    assert [a.id for a in attachments.list_all()] == [catalog.id]


def test_get_many_by_targets_returns_the_attached_ones(attachments: TableDiscoveryPolicyAttachmentsRepo):
    """Only the targets that have an attachment are returned; no target returns nothing."""
    catalog, table = _attach(CATALOG), _attach(TABLE, "manage-all")
    attachments.create(catalog)
    attachments.create(table)

    found = attachments.get_many_by_targets([TABLE, NAMESPACE, CATALOG])

    assert sorted(a.id.value for a in found) == sorted([catalog.id.value, table.id.value])
    assert attachments.get_many_by_targets([]) == []
    assert attachments.get_by_target(NAMESPACE) is None


def test_an_attachment_to_an_unknown_policy_is_refused(tmp_path: Path):
    """The SQL attachment's policy id is a foreign key to the stored discovery policies."""
    engine = create_engine(f"sqlite:///{tmp_path / 'fk.sqlite'}")
    event.listen(engine, "connect", lambda dbapi_connection, _: dbapi_connection.execute("PRAGMA foreign_keys=ON"))
    create_schema(engine)
    _store_policies(engine)
    repo = TableDiscoveryPolicyAttachmentsSqlRepo(engine)

    with pytest.raises(ConflictError):
        repo.create(TableDiscoveryPolicyAttachment.attach(CATALOG, TableDiscoveryPolicyId.new(), NOW))

    repo.create(_attach(CATALOG))
    assert [a.policy_id for a in repo.list_all()] == [POLICY_IDS["manage-sales"]]
