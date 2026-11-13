"""Composition building blocks shared by the component entry points."""

from __future__ import annotations

from bootstrap.container.activities import Activities
from bootstrap.container.admission_lease_seconds import admission_lease_seconds
from bootstrap.container.apply_worker_startup import apply_worker_startup
from bootstrap.container.build_activities import build_activities
from bootstrap.container.build_api_app import build_api_app
from bootstrap.container.build_candidate_selection import build_candidate_selection
from bootstrap.container.build_catalog_factory import build_catalog_factory
from bootstrap.container.build_catalog_web_use_cases import build_catalog_web_use_cases
from bootstrap.container.build_connected_use_cases import build_connected_use_cases
from bootstrap.container.build_engine import build_engine
from bootstrap.container.build_event_log_filesystem import (
    build_event_log_filesystem,
)
from bootstrap.container.build_gateways import build_gateways
from bootstrap.container.build_k8s_api import build_k8s_api
from bootstrap.container.build_k8s_core_api import build_k8s_core_api
from bootstrap.container.build_openapi_document import build_openapi_document
from bootstrap.container.build_polaris_http_client import build_polaris_http_client
from bootstrap.container.build_priority_sla import build_priority_sla
from bootstrap.container.build_priority_weights import build_priority_weights
from bootstrap.container.build_repositories import build_repositories
from bootstrap.container.build_size_memory import build_size_memory
from bootstrap.container.build_spark_config import build_spark_config
from bootstrap.container.build_use_cases import build_use_cases
from bootstrap.container.build_web_use_cases import build_web_use_cases
from bootstrap.container.build_worker import WORKFLOWS, build_worker
from bootstrap.container.compaction_claim_lease import compaction_claim_lease
from bootstrap.container.configure_logging import configure_logging
from bootstrap.container.connect_temporal import connect_temporal
from bootstrap.container.create_api_app import create_api_app
from bootstrap.container.event_log_base import (
    event_log_base,
)
from bootstrap.container.gateways import Gateways
from bootstrap.container.lazy_client import LazyClient
from bootstrap.container.load_k8s_config import load_k8s_config
from bootstrap.container.repositories import Repositories
from bootstrap.container.run_event_consumer import run_event_consumer
from bootstrap.container.run_migrations import run_migrations
from bootstrap.container.spark_memory_bytes import spark_memory_bytes
from bootstrap.container.use_cases import UseCases

__all__ = [
    "Activities",
    "Gateways",
    "LazyClient",
    "Repositories",
    "UseCases",
    "WORKFLOWS",
    "admission_lease_seconds",
    "apply_worker_startup",
    "build_activities",
    "build_api_app",
    "build_candidate_selection",
    "build_catalog_factory",
    "build_catalog_web_use_cases",
    "build_connected_use_cases",
    "build_engine",
    "build_event_log_filesystem",
    "build_gateways",
    "build_k8s_api",
    "build_k8s_core_api",
    "build_openapi_document",
    "build_polaris_http_client",
    "build_priority_sla",
    "build_priority_weights",
    "build_repositories",
    "build_size_memory",
    "compaction_claim_lease",
    "build_spark_config",
    "build_use_cases",
    "build_web_use_cases",
    "build_worker",
    "configure_logging",
    "connect_temporal",
    "create_api_app",
    "event_log_base",
    "load_k8s_config",
    "run_event_consumer",
    "run_migrations",
    "spark_memory_bytes",
]
