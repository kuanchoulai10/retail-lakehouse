"""Test the table maintenance policy use case services."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    MaintenancePolicyContent,
    TableMaintenancePolicyName,
)
from context.table_maintenance.application.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    CreateTableMaintenancePolicyUseCaseInput,
    DeleteTableMaintenancePolicyUseCaseInput,
    EnsureDefaultTableMaintenancePolicyUseCaseInput,
    GetTableMaintenancePolicyUseCaseInput,
    GetTableMaintenancePolicyVersionUseCaseInput,
    ListTableMaintenancePoliciesUseCaseInput,
    UpdateTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.service.table_maintenance_policy import (
    CreateTableMaintenancePolicyService,
    DeleteTableMaintenancePolicyService,
    EnsureDefaultTableMaintenancePolicyService,
    GetTableMaintenancePolicyService,
    GetTableMaintenancePolicyVersionService,
    ListTableMaintenancePoliciesService,
    UpdateTableMaintenancePolicyService,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policies_repo import (
    InMemoryTableMaintenancePoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policy_attachments_repo import (
    InMemoryTableMaintenancePolicyAttachmentsRepo,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CONTENT = MaintenancePolicyContent.platform_default().to_primitives()


def _create(repo, name="gold", content=None):
    return CreateTableMaintenancePolicyService(repo, clock=lambda: NOW).execute(
        CreateTableMaintenancePolicyUseCaseInput(name=name, content=content or CONTENT)
    )


def test_create_then_get_and_list():
    """A created policy is readable at version 1 and listed."""
    repo = InMemoryTableMaintenancePoliciesRepo()
    out = _create(repo)
    assert out.version == 1
    got = GetTableMaintenancePolicyService(repo).execute(GetTableMaintenancePolicyUseCaseInput(name="gold"))
    assert got.content == CONTENT
    listed = ListTableMaintenancePoliciesService(repo).execute(ListTableMaintenancePoliciesUseCaseInput())
    assert [i.name for i in listed.items] == ["gold"]


def test_get_missing_is_not_found():
    """Getting an unknown policy is NotFoundError."""
    with pytest.raises(NotFoundError):
        GetTableMaintenancePolicyService(InMemoryTableMaintenancePoliciesRepo()).execute(
            GetTableMaintenancePolicyUseCaseInput(name="nope")
        )


def test_replace_increments_version_and_keeps_old_version_readable():
    """An update makes version 2 and version 1 stays readable."""
    repo = InMemoryTableMaintenancePoliciesRepo()
    _create(repo)
    new_content = {**CONTENT, "dry_run": True}
    out = UpdateTableMaintenancePolicyService(repo, clock=lambda: NOW + timedelta(hours=1)).execute(
        UpdateTableMaintenancePolicyUseCaseInput(name="gold", content=new_content, version=1)
    )
    assert out.version == 2
    old = repo.get_version(TableMaintenancePolicyName("gold"), 1)
    assert old is not None
    assert old.content.to_primitives() == CONTENT
    via_service = GetTableMaintenancePolicyVersionService(repo).execute(
        GetTableMaintenancePolicyVersionUseCaseInput(name="gold", version=2)
    )
    assert via_service.content == new_content


def test_replace_with_stale_version_conflicts():
    """A stale version is ConflictError and the repo is unchanged."""
    repo = InMemoryTableMaintenancePoliciesRepo()
    _create(repo)
    service = UpdateTableMaintenancePolicyService(repo, clock=lambda: NOW)
    service.execute(
        UpdateTableMaintenancePolicyUseCaseInput(name="gold", content={**CONTENT, "dry_run": True}, version=1)
    )
    with pytest.raises(ConflictError):
        service.execute(UpdateTableMaintenancePolicyUseCaseInput(name="gold", content=CONTENT, version=1))
    policy = repo.get(TableMaintenancePolicyName("gold"))
    assert policy is not None
    assert policy.version == 2
    assert policy.content.dry_run is True


def test_update_missing_is_not_found():
    """Updating an unknown policy is NotFoundError."""
    with pytest.raises(NotFoundError):
        UpdateTableMaintenancePolicyService(InMemoryTableMaintenancePoliciesRepo()).execute(
            UpdateTableMaintenancePolicyUseCaseInput(name="nope", content=CONTENT, version=1)
        )


def test_duplicate_name_conflicts():
    """Creating a taken name is ConflictError."""
    repo = InMemoryTableMaintenancePoliciesRepo()
    _create(repo)
    with pytest.raises(ConflictError):
        _create(repo)


def test_invalid_name_is_422():
    """A name with a space is ValidationError."""
    with pytest.raises(ValidationError):
        _create(InMemoryTableMaintenancePoliciesRepo(), name="has space")


def test_invalid_content_is_422():
    """Content that breaks an invariant is ValidationError."""
    bad = MaintenancePolicyContent.platform_default().to_primitives()
    bad["operations"]["remove_orphan_files"]["execution_policy"]["older_than_seconds"] = 60
    with pytest.raises(ValidationError):
        _create(InMemoryTableMaintenancePoliciesRepo(), content=bad)


def test_delete_removes_policy():
    """Deleting a policy removes it."""
    repo = InMemoryTableMaintenancePoliciesRepo()
    _create(repo)
    DeleteTableMaintenancePolicyService(repo, InMemoryTableMaintenancePolicyAttachmentsRepo()).execute(
        DeleteTableMaintenancePolicyUseCaseInput(name="gold")
    )
    assert repo.get(TableMaintenancePolicyName("gold")) is None


def test_delete_missing_is_not_found():
    """Deleting an unknown policy is NotFoundError."""
    with pytest.raises(NotFoundError):
        DeleteTableMaintenancePolicyService(
            InMemoryTableMaintenancePoliciesRepo(), InMemoryTableMaintenancePolicyAttachmentsRepo()
        ).execute(DeleteTableMaintenancePolicyUseCaseInput(name="nope"))


def test_delete_default_conflicts():
    """The default policy cannot be deleted."""
    repo = InMemoryTableMaintenancePoliciesRepo()
    EnsureDefaultTableMaintenancePolicyService(repo, clock=lambda: NOW).execute(
        EnsureDefaultTableMaintenancePolicyUseCaseInput()
    )
    with pytest.raises(ConflictError):
        DeleteTableMaintenancePolicyService(repo, InMemoryTableMaintenancePolicyAttachmentsRepo()).execute(
            DeleteTableMaintenancePolicyUseCaseInput(name="default")
        )


def test_ensure_default_is_idempotent():
    """Ensuring the default twice leaves one policy at version 1."""
    repo = InMemoryTableMaintenancePoliciesRepo()
    service = EnsureDefaultTableMaintenancePolicyService(repo, clock=lambda: NOW)
    assert service.execute(EnsureDefaultTableMaintenancePolicyUseCaseInput()).created is True
    assert service.execute(EnsureDefaultTableMaintenancePolicyUseCaseInput()).created is False
    policies = repo.list_all()
    assert [(p.id.value, p.version) for p in policies] == [("default", 1)]
    assert policies[0].content == MaintenancePolicyContent.platform_default()
