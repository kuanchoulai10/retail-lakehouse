"""Provide use case dependencies."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from application.service.outbox.event_serializer import EventSerializer
from application.service.catalog.get_table import GetTableService
from application.service.catalog.list_branches import ListBranchesService
from application.service.catalog.list_namespaces import (
    ListNamespacesService,
)
from application.service.catalog.list_snapshots import ListSnapshotsService
from application.service.catalog.list_tables import ListTablesService
from application.service.catalog.list_tags import ListTagsService
from application.service.job.create_job import CreateJobService
from application.service.job.get_job import GetJobService
from application.service.job.list_jobs import ListJobsService
from application.service.job.update_job import UpdateJobService
from application.service.job_run.create_job_run import CreateJobRunService
from application.service.job_run.get_job_run import GetJobRunService
from application.service.job_run.list_job_runs import ListJobRunsService

from bootstrap.dependencies.catalog import get_catalog_reader
from bootstrap.dependencies.outbox import get_event_serializer, get_outbox_repo
from bootstrap.dependencies.repos import (
    get_job_runs_repo,
    get_jobs_repo,
)

if TYPE_CHECKING:
    from application.port.inbound import (
        CreateJobRunUseCase,
        CreateJobUseCase,
        GetJobRunUseCase,
        GetJobUseCase,
        GetTableUseCase,
        ListBranchesUseCase,
        ListJobRunsUseCase,
        ListJobsUseCase,
        ListNamespacesUseCase,
        ListSnapshotsUseCase,
        ListTablesUseCase,
        ListTagsUseCase,
        UpdateJobUseCase,
    )
    from application.port.outbound.catalog.read_catalog.gateway import (
        ReadCatalogGateway,
    )
    from application.port.outbound.event_outbox.event_outbox_store import (
        EventOutboxStore,
    )
    from application.port.outbound.job_run.job_runs_repo import JobRunsRepo
    from application.port.outbound.job.jobs_repo import JobsRepo


def get_create_job_use_case(
    repo: JobsRepo = Depends(get_jobs_repo),
    outbox_repo: EventOutboxStore = Depends(get_outbox_repo),
    serializer: EventSerializer = Depends(get_event_serializer),
) -> CreateJobUseCase:
    """Provide the CreateJob use case with injected dependencies."""
    return CreateJobService(repo, outbox_repo, serializer)


def get_get_job_use_case(
    repo: JobsRepo = Depends(get_jobs_repo),
) -> GetJobUseCase:
    """Provide the GetJob use case with injected dependencies."""
    return GetJobService(repo)


def get_list_jobs_use_case(
    repo: JobsRepo = Depends(get_jobs_repo),
) -> ListJobsUseCase:
    """Provide the ListJobs use case with injected dependencies."""
    return ListJobsService(repo)


def get_update_job_use_case(
    repo: JobsRepo = Depends(get_jobs_repo),
    outbox_repo: EventOutboxStore = Depends(get_outbox_repo),
    serializer: EventSerializer = Depends(get_event_serializer),
) -> UpdateJobUseCase:
    """Provide the UpdateJob use case with injected dependencies."""
    return UpdateJobService(repo, outbox_repo, serializer)


def get_create_job_run_use_case(
    repo: JobsRepo = Depends(get_jobs_repo),
    job_runs_repo: JobRunsRepo = Depends(get_job_runs_repo),
    outbox_repo: EventOutboxStore = Depends(get_outbox_repo),
    serializer: EventSerializer = Depends(get_event_serializer),
) -> CreateJobRunUseCase:
    """Provide the CreateJobRun use case with injected dependencies."""
    return CreateJobRunService(repo, job_runs_repo, outbox_repo, serializer)


def get_list_job_runs_use_case(
    repo: JobRunsRepo = Depends(get_job_runs_repo),
) -> ListJobRunsUseCase:
    """Provide the ListJobRuns use case with injected dependencies."""
    return ListJobRunsService(repo)


def get_get_job_run_use_case(
    repo: JobRunsRepo = Depends(get_job_runs_repo),
) -> GetJobRunUseCase:
    """Provide the GetJobRun use case with injected dependencies."""
    return GetJobRunService(repo)


# --- Catalog use cases ---


def get_list_namespaces_use_case(
    reader: ReadCatalogGateway = Depends(get_catalog_reader),
) -> ListNamespacesUseCase:
    """Provide the ListNamespaces use case."""
    return ListNamespacesService(reader)


def get_list_tables_use_case(
    reader: ReadCatalogGateway = Depends(get_catalog_reader),
) -> ListTablesUseCase:
    """Provide the ListTables use case."""
    return ListTablesService(reader)


def get_get_table_use_case(
    reader: ReadCatalogGateway = Depends(get_catalog_reader),
) -> GetTableUseCase:
    """Provide the GetTable use case."""
    return GetTableService(reader)


def get_list_snapshots_use_case(
    reader: ReadCatalogGateway = Depends(get_catalog_reader),
) -> ListSnapshotsUseCase:
    """Provide the ListSnapshots use case."""
    return ListSnapshotsService(reader)


def get_list_branches_use_case(
    reader: ReadCatalogGateway = Depends(get_catalog_reader),
) -> ListBranchesUseCase:
    """Provide the ListBranches use case."""
    return ListBranchesService(reader)


def get_list_tags_use_case(
    reader: ReadCatalogGateway = Depends(get_catalog_reader),
) -> ListTagsUseCase:
    """Provide the ListTags use case."""
    return ListTagsService(reader)
