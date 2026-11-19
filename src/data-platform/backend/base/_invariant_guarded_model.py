"""Internal helper: the Pydantic model every model base extends, raising InvariantViolation.

``ValueObject``, ``Entity``, ``EntityId``, ``DomainEvent`` and the inbound port
models ``UseCaseInput`` and ``UseCaseOutput`` extend ``InvariantGuardedModel``
first, so each way Pydantic validates one of them (keyword or positional
construction, ``model_validate``, ``model_validate_json``,
``model_validate_strings`` and assignment) turns a ``ValidationError`` into an
``InvariantViolation`` chained from it. A violation raised by an inner model
inside an outer model's validator reaches Pydantic as a ``ValueError``, so it
comes out of the outer model as one ``InvariantViolation`` with the inner line.

A base whose refusal is never the caller's fault overrides ``_refusal`` to
raise another exception: ``UseCaseOutput`` raises ``TypeError``, because only
our own services build outputs, so a refused output is a server bug.

Changing a frozen model in place, or deleting a field of any model, is a
programming error rather than refused data, so it raises Python's builtin
``AttributeError`` (as a frozen dataclass does), never ``InvariantViolation``.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, ClassVar, Self

from pydantic import BaseModel, ValidationError

from base.invariant_violation import InvariantViolation

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pydantic.config import ExtraValues


_FROZEN_ERRORS = frozenset({"frozen_instance", "frozen_field"})


@contextmanager
def _raising_refusal(model_class: type[InvariantGuardedModel]) -> Iterator[None]:
    """Re-raise a Pydantic ``ValidationError`` as the class's ``_refusal``, chained from it."""
    try:
        yield
    except ValidationError as exc:
        raise model_class._refusal(exc) from exc


@contextmanager
def _refusing_frozen_changes(model: InvariantGuardedModel) -> Iterator[None]:
    """Re-raise Pydantic's refusal to change a frozen model or field as an ``AttributeError``."""
    try:
        yield
    except ValidationError as exc:
        if any(error["type"] in _FROZEN_ERRORS for error in exc.errors()):
            raise AttributeError(f"{type(model).__name__} is immutable{model._immutable_hint}") from None
        raise


class InvariantGuardedModel(BaseModel):
    """A Pydantic model that raises ``InvariantViolation`` wherever it validates.

    Changing it when it is frozen, or deleting one of its fields, raises
    ``AttributeError``; ``_immutable_hint`` ends that message (a value object
    points at ``with_changes``).
    """

    _immutable_hint: ClassVar[str] = ""

    @classmethod
    def _refusal(cls, exc: ValidationError) -> Exception:
        """Return the exception raised for refused data: an ``InvariantViolation``, its line from ``exc``."""
        return InvariantViolation.from_error(exc)

    def __init__(self, /, *args: Any, **data: Any) -> None:  # noqa: ANN401
        """Validate the data as the next base does (``EntityId`` takes its root positionally)."""
        __tracebackhide__ = True
        with _raising_refusal(type(self)):
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
        with _raising_refusal(cls):
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
        with _raising_refusal(cls):
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
        with _raising_refusal(cls):
            return super().model_validate_strings(
                obj, strict=strict, extra=extra, context=context, by_alias=by_alias, by_name=by_name
            )

    def __setattr__(self, name: str, value: Any) -> None:  # noqa: ANN401
        """Assign as Pydantic does: a refused value raises ``InvariantViolation``, a frozen model ``AttributeError``."""
        with _raising_refusal(type(self)), _refusing_frozen_changes(self):
            super().__setattr__(name, value)

    def __delattr__(self, name: str) -> None:
        """Refuse to delete a field with ``AttributeError``; other attributes are deleted as Pydantic does."""
        cls = type(self)
        if name in cls.model_fields and not cls.model_config.get("frozen"):
            raise AttributeError(f"{cls.__name__}.{name} is a field and cannot be deleted; assign a new value instead")
        with _refusing_frozen_changes(self):
            super().__delattr__(name)
