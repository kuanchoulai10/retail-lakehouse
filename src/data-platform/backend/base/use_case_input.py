"""Define the Pydantic UseCaseInput base class."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Self

from pydantic import ConfigDict

from base._inheritance_guard import enforce_max_depth
from base._invariant_guarded_model import InvariantGuardedModel
from base.invariant_violation import InvariantViolation

if TYPE_CHECKING:
    from collections.abc import Mapping


class UseCaseInput(InvariantGuardedModel):
    """The self-validating request an inbound port takes.

    Every entry point (a web router, a Temporal activity, an event consumer)
    builds the same input, so it is validated once, here: strict (no
    coercion: ``"1"`` is not an ``int``, a ``list`` is not a ``tuple``),
    frozen, and, when built in code, unknown keys refused, so a typo fails.
    Building one with refused data raises ``InvariantViolation``; assigning
    to a field raises ``AttributeError``.

    Fields hold primitives and standard-library types only (``str``, ``int``,
    ``float``, ``bool``, ``None``, ``datetime``, ``timedelta``, ``tuple``,
    ``dict``; a sequence is a ``tuple``, never a ``list``) and classes nested
    one level inside the input, each extending ``UseCaseInput`` directly;
    never a domain type.

    A caller holding a dict of JSON primitives (a Temporal or Kafka payload)
    builds the input with ``from_primitives``, a tolerant reader that ignores
    keys the input does not declare; code builds it by keyword.

    Usage::

        class ListTableCommitsUseCaseInput(UseCaseInput):
            uuid: str
            since: datetime | None = None
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """Enforce a flat hierarchy: a concrete input, or a class nested in one, extends UseCaseInput directly."""
        super().__pydantic_init_subclass__(**kwargs)
        enforce_max_depth(cls, UseCaseInput, 1)

    @classmethod
    def from_primitives(cls, data: Mapping[str, Any]) -> Self:
        """Build from JSON-compatible primitives, validated in strict JSON mode, as a tolerant reader.

        An ISO 8601 string becomes a ``datetime`` and a JSON array a ``tuple``
        field. A key the input does not declare is ignored at every depth,
        nested classes included, so a payload from a newer sender (a workflow
        on a newer pod during a rolling deploy) still reads; a missing
        required key or a mistyped value is refused. Input that is not
        JSON-compatible (a ``datetime`` object, a mapping that is not a
        ``dict``, NaN or Infinity) raises ``InvariantViolation``, like any
        refused input.
        """
        try:
            payload = json.dumps(data, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise InvariantViolation(f"{cls.__name__} input must be JSON-compatible primitives: {exc}") from exc
        return cls.model_validate_json(payload, extra="ignore")
