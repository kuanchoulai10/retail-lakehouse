"""Provide the run_migrations function."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from adapter.outbound.sql.create_schema import create_schema
from application.service.policy_template.create_policy_template import (
    CreatePolicyTemplateService,
)
from application.service.policy_template.list_policy_templates import (
    ListPolicyTemplatesService,
)
from bootstrap.container.build_repositories import build_repositories
from bootstrap.container.seed_default_template import seed_default_template

if TYPE_CHECKING:
    from sqlalchemy import Engine

logger = logging.getLogger(__name__)


def run_migrations(engine: Engine) -> None:
    """Create the missing tables, then seed the default template once.

    ``create_all`` only adds missing tables; it never alters existing ones. No
    discovery rule is seeded.
    """
    create_schema(engine)
    templates = build_repositories(engine).policy_templates
    created = seed_default_template(
        ListPolicyTemplatesService(templates), CreatePolicyTemplateService(templates)
    )
    logger.info("schema ready; default template %s", "created" if created else "kept")
