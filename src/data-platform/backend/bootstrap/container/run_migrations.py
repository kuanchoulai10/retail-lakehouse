"""Provide the run_migrations function."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from bootstrap.container.build_repositories import build_repositories
from context.table_maintenance.adapter.outbound.shared.sql import create_schema
from context.table_maintenance.application.port.inbound.table_discovery_policy import (
    EnsureDefaultTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    EnsureDefaultTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.service.table_discovery_policy import (
    EnsureDefaultTableDiscoveryPolicyService,
)
from context.table_maintenance.application.service.table_maintenance_policy import (
    EnsureDefaultTableMaintenancePolicyService,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine

logger = logging.getLogger(__name__)


def run_migrations(engine: Engine) -> None:
    """Create the missing tables, then seed the default maintenance policy and the default discovery policy once.

    ``create_schema`` adds missing tables and applies its idempotent column
    upgrades. No discovery rule is seeded.
    """
    create_schema(engine)
    repos = build_repositories(engine)
    maintenance_created = (
        EnsureDefaultTableMaintenancePolicyService(repos.table_maintenance_policies)
        .execute(EnsureDefaultTableMaintenancePolicyUseCaseInput())
        .created
    )
    discovery_created = (
        EnsureDefaultTableDiscoveryPolicyService(repos.table_discovery_policies)
        .execute(EnsureDefaultTableDiscoveryPolicyUseCaseInput())
        .created
    )
    logger.info(
        "schema ready; default maintenance policy %s; default discovery policy %s",
        "created" if maintenance_created else "kept",
        "created" if discovery_created else "kept",
    )
