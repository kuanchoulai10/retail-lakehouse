"""Define the translate_domain_errors context manager."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from base import validation_message
from context.table_maintenance.application.domain.model.compaction_candidate import (
    InvalidCandidateTransition,
)
from context.table_maintenance.application.domain.model.table import (
    InvalidTableTransition,
)
from context.table_maintenance.application.domain.model.table_discovery_rules import (
    StaleDiscoveryRulesVersion,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    StalePolicyVersion,
)
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    InvalidRunTransition,
)
from context.table_maintenance.application.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


@contextmanager
def translate_domain_errors() -> Iterator[None]:
    """Translate domain and repo errors into application exceptions.

    InvalidTableTransition, InvalidRunTransition, InvalidCandidateTransition,
    StalePolicyVersion and StaleDiscoveryRulesVersion become ConflictError, any
    other ValueError (which covers invalid settings and rules, Pydantic's
    included) becomes ValidationError with a one-line message, and a repo
    LookupError becomes NotFoundError. Application exceptions pass through.
    """
    try:
        yield
    except (
        InvalidTableTransition,
        InvalidRunTransition,
        InvalidCandidateTransition,
        StalePolicyVersion,
        StaleDiscoveryRulesVersion,
    ) as exc:
        raise ConflictError(str(exc)) from exc
    except ValueError as exc:
        raise ValidationError(validation_message(exc)) from exc
    except LookupError as exc:
        raise NotFoundError(str(exc)) from exc
