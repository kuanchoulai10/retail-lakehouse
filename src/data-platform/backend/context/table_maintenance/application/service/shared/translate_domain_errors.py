"""Define the translate_domain_errors context manager."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_maintenance_run import (
    InvalidRunTransition,
)
from context.table_maintenance.application.domain.model.table import (
    InvalidTableTransition,
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

    InvalidTableTransition and InvalidRunTransition become ConflictError, any
    other ValueError (which covers invalid settings and rules) becomes
    ValidationError, and a repo LookupError becomes NotFoundError. Application
    exceptions pass through.
    """
    try:
        yield
    except (InvalidTableTransition, InvalidRunTransition) as exc:
        raise ConflictError(str(exc)) from exc
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    except LookupError as exc:
        raise NotFoundError(str(exc)) from exc
