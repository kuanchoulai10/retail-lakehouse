"""Internal helper: the Pydantic model every model base extends, raising InvariantViolation.

``ValueObject``, ``Entity``, ``EntityId`` and ``DomainEvent`` extend
``InvariantGuardedModel`` first, so each way Pydantic validates one of them
(keyword or positional construction, ``model_validate``, ``model_validate_json``,
``model_validate_strings`` and assignment) turns a ``ValidationError`` into an
``InvariantViolation`` chained from it. A violation raised by an inner model
inside an outer model's validator reaches Pydantic as a ``ValueError``, so it
comes out of the outer model as one ``InvariantViolation`` with the inner line.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Self

from pydantic import BaseModel, ValidationError

from base.invariant_violation import InvariantViolation

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pydantic.config import ExtraValues


@contextmanager
def _raising_invariant_violation() -> Iterator[None]:
    """Re-raise a Pydantic ``ValidationError`` as an ``InvariantViolation`` chained from it."""
    try:
        yield
    except ValidationError as exc:
        raise InvariantViolation.from_error(exc) from exc


class InvariantGuardedModel(BaseModel):
    """A Pydantic model that raises ``InvariantViolation`` wherever it validates."""

    def __init__(self, /, *args: Any, **data: Any) -> None:  # noqa: ANN401
        """Validate the data as the next base does (``EntityId`` takes its root positionally)."""
        __tracebackhide__ = True
        with _raising_invariant_violation():
            super().__init__(*args, **data)

    # Pydantic calls a model's own ``__init__`` when validating it nested inside another
    # model unless the init is marked a base init; this one only wraps, so it is.
    __init__.__pydantic_base_init__ = True  # ty: ignore[unresolved-attribute]

    @classmethod
    def model_validate(
        cls,
        obj: Any,  # noqa: ANN401
        *,
        strict: bool | None = None,
        extra: ExtraValues | None = None,
        from_attributes: bool | None = None,
        context: Any | None = None,  # noqa: ANN401
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        """Validate ``obj`` as Pydantic does, raising ``InvariantViolation``."""
        with _raising_invariant_violation():
            return super().model_validate(
                obj,
                strict=strict,
                extra=extra,
                from_attributes=from_attributes,
                context=context,
                by_alias=by_alias,
                by_name=by_name,
            )

    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        extra: ExtraValues | None = None,
        context: Any | None = None,  # noqa: ANN401
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        """Validate ``json_data`` as Pydantic does, raising ``InvariantViolation``."""
        with _raising_invariant_violation():
            return super().model_validate_json(
                json_data, strict=strict, extra=extra, context=context, by_alias=by_alias, by_name=by_name
            )

    @classmethod
    def model_validate_strings(
        cls,
        obj: Any,  # noqa: ANN401
        *,
        strict: bool | None = None,
        extra: ExtraValues | None = None,
        context: Any | None = None,  # noqa: ANN401
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        """Validate string data as Pydantic does, raising ``InvariantViolation``."""
        with _raising_invariant_violation():
            return super().model_validate_strings(
                obj, strict=strict, extra=extra, context=context, by_alias=by_alias, by_name=by_name
            )

    def __setattr__(self, name: str, value: Any) -> None:  # noqa: ANN401
        """Assign as Pydantic does (validated or refused as frozen), raising ``InvariantViolation``."""
        with _raising_invariant_violation():
            super().__setattr__(name, value)
