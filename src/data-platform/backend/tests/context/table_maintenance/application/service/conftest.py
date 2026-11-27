"""Shared fixtures for application service tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    EnsureDefaultTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.service.table_maintenance_policy import (
    EnsureDefaultTableMaintenancePolicyService,
)
from context.table_maintenance.application.service.table_maintenance_policy_attachment import (
    ResolveApplicableTableMaintenancePolicyService,
)
from tests.context.table_maintenance.fakes.fake_read_maintenance_job_gateway import (
    FakeReadMaintenanceJobGateway,
)
from tests.context.table_maintenance.fakes.fake_read_table_metadata_gateway import (
    FakeReadTableMetadataGateway,
)
from tests.context.table_maintenance.fakes.in_memory_catalog_discoveries_repo import (
    InMemoryCatalogDiscoveriesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_catalogs_repo import InMemoryCatalogsRepo
from tests.context.table_maintenance.fakes.in_memory_namespaces_repo import InMemoryNamespacesRepo
from tests.context.table_maintenance.fakes.in_memory_policy_placements_store import InMemoryPolicyPlacementsStore
from tests.context.table_maintenance.fakes.in_memory_table_discovery_policies_repo import (
    InMemoryTableDiscoveryPoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policies_repo import (
    InMemoryTableMaintenancePoliciesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_policy_attachments_repo import (
    InMemoryTableMaintenancePolicyAttachmentsRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_runs_repo import (
    InMemoryTableMaintenanceRunsRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_metrics_store import (
    InMemoryTableMetricsStore,
)
from tests.context.table_maintenance.fakes.in_memory_tables_repo import (
    InMemoryTablesRepo,
)
from tests.context.table_maintenance.fakes.recording_delete_maintenance_job_gateway import (
    RecordingDeleteMaintenanceJobGateway,
)
from tests.context.table_maintenance.fakes.recording_send_discovery_request_gateway import (
    RecordingSendDiscoveryRequestGateway,
)
from tests.context.table_maintenance.fakes.recording_send_maintenance_result_gateway import (
    RecordingSendMaintenanceResultGateway,
)
from tests.context.table_maintenance.fakes.recording_send_table_change_gateway import (
    RecordingSendTableChangeGateway,
)
from tests.context.table_maintenance.fakes.recording_submit_maintenance_job_gateway import (
    RecordingSubmitMaintenanceJobGateway,
)

if TYPE_CHECKING:
    from collections.abc import Callable

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)


@pytest.fixture
def now() -> datetime:
    """Provide the fixed current time."""
    return NOW


@pytest.fixture
def clock() -> Callable[[], datetime]:
    """Provide a clock that always returns the fixed current time."""
    return lambda: NOW


@pytest.fixture
def new_id() -> Callable[[], str]:
    """Provide a discovery rule id generator that returns dr-…001, dr-…002 and so on (26 base32 characters)."""
    counter = iter(range(1, 1000))
    return lambda: f"dr-{next(counter):026d}"


@pytest.fixture
def discovery_policies() -> InMemoryTableDiscoveryPoliciesRepo:
    """Provide an in-memory discovery policies repository holding no policy (a scan never reads the default)."""
    return InMemoryTableDiscoveryPoliciesRepo()


@pytest.fixture
def catalogs_repo() -> InMemoryCatalogsRepo:
    """Provide an in-memory catalogs repository holding no catalog."""
    return InMemoryCatalogsRepo()


@pytest.fixture
def namespaces_repo() -> InMemoryNamespacesRepo:
    """Provide an in-memory namespaces repository holding no namespace."""
    return InMemoryNamespacesRepo()


@pytest.fixture
def placements(
    catalogs_repo: InMemoryCatalogsRepo, namespaces_repo: InMemoryNamespacesRepo, tables_repo: InMemoryTablesRepo
) -> InMemoryPolicyPlacementsStore:
    """Provide the policy placements, read from the catalogs, namespaces and tables repositories."""
    return InMemoryPolicyPlacementsStore(catalogs_repo, namespaces_repo, tables_repo)


@pytest.fixture
def discoveries_repo() -> InMemoryCatalogDiscoveriesRepo:
    """Provide an in-memory catalog discoveries repository holding no discovery."""
    return InMemoryCatalogDiscoveriesRepo()


@pytest.fixture
def tables_repo() -> InMemoryTablesRepo:
    """Provide an in-memory tables repository."""
    return InMemoryTablesRepo()


@pytest.fixture
def metrics_store() -> InMemoryTableMetricsStore:
    """Provide an in-memory table metrics store."""
    return InMemoryTableMetricsStore()


@pytest.fixture
def signals() -> RecordingSendTableChangeGateway:
    """Provide a table change gateway that records the changes sent."""
    return RecordingSendTableChangeGateway()


@pytest.fixture
def catalog() -> FakeReadTableMetadataGateway:
    """Provide a fake catalog metadata gateway."""
    return FakeReadTableMetadataGateway()


@pytest.fixture
def runs_repo() -> InMemoryTableMaintenanceRunsRepo:
    """Provide an in-memory maintenance runs repository."""
    return InMemoryTableMaintenanceRunsRepo()


@pytest.fixture
def submit_job() -> RecordingSubmitMaintenanceJobGateway:
    """Provide a submit job gateway that records its calls."""
    return RecordingSubmitMaintenanceJobGateway()


@pytest.fixture
def read_job() -> FakeReadMaintenanceJobGateway:
    """Provide a fake job status gateway."""
    return FakeReadMaintenanceJobGateway()


@pytest.fixture
def delete_job() -> RecordingDeleteMaintenanceJobGateway:
    """Provide a delete job gateway that records its calls."""
    return RecordingDeleteMaintenanceJobGateway()


@pytest.fixture
def results() -> RecordingSendMaintenanceResultGateway:
    """Provide a result gateway that records the results sent."""
    return RecordingSendMaintenanceResultGateway()


@pytest.fixture
def discovery_requests() -> RecordingSendDiscoveryRequestGateway:
    """Provide a discovery request gateway that records its requests."""
    return RecordingSendDiscoveryRequestGateway()


@pytest.fixture
def log() -> list[tuple[str, str]]:
    """Provide the shared list that the in-memory repositories write their calls to."""
    return []


@pytest.fixture
def policies_repo() -> InMemoryTableMaintenancePoliciesRepo:
    """Provide a policies repo holding the platform default policy (version 1)."""
    repo = InMemoryTableMaintenancePoliciesRepo()
    EnsureDefaultTableMaintenancePolicyService(repo, clock=lambda: NOW).execute(
        EnsureDefaultTableMaintenancePolicyUseCaseInput()
    )
    return repo


@pytest.fixture
def attachments_repo() -> InMemoryTableMaintenancePolicyAttachmentsRepo:
    """Provide an empty policy attachments repo."""
    return InMemoryTableMaintenancePolicyAttachmentsRepo()


@pytest.fixture
def resolve_applicable_policy(
    policies_repo: InMemoryTableMaintenancePoliciesRepo,
    attachments_repo: InMemoryTableMaintenancePolicyAttachmentsRepo,
    catalog: FakeReadTableMetadataGateway,
    tables_repo: InMemoryTablesRepo,
) -> ResolveApplicableTableMaintenancePolicyService:
    """Provide the applicable policy resolution on the fakes."""
    return ResolveApplicableTableMaintenancePolicyService(policies_repo, attachments_repo, catalog, tables_repo)
