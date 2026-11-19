"""Define the Pydantic UseCaseOutput base class."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import ConfigDict

from base._inheritance_guard import enforce_max_depth
from base._invariant_guarded_model import InvariantGuardedModel
from base.invariant_violation import InvariantViolation

if TYPE_CHECKING:
    from pydantic import ValidationError


class UseCaseOutput(InvariantGuardedModel):
    """The result an inbound port returns.

    Strict (a service passes the declared type: a ``tuple`` for a ``tuple``
    field), frozen, and unknown keys refused. Only our own services build an
    output, so building one with refused data is a server bug, not a client
    error: it raises Python's builtin ``TypeError`` chained from Pydantic's
    error (never ``InvariantViolation``, which every edge answers as the
    caller's fault), so it reaches the edge as a logged 500 or a retryable
    failure. Assigning to a field raises ``AttributeError``.

    Fields hold primitives and standard-library types only (``str``, ``int``,
    ``float``, ``bool``, ``None``, ``datetime``, ``timedelta``, ``tuple``,
    ``dict``; a sequence is a ``tuple``, never a ``list``) and classes nested
    one level inside the output, each extending ``UseCaseOutput`` directly and
    named by what it holds; never a domain type, so adapters never see the
    domain.

    Usage::

        class ListTableCommitsUseCaseOutput(UseCaseOutput):
            class Commit(UseCaseOutput):
                snapshot_id: int

            items: tuple[Commit, ...]
            truncated: bool
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    @classmethod
    def _refusal(cls, exc: ValidationError) -> Exception:
        """Return a ``TypeError`` naming the output and the first refused field: a refused output is a server bug."""
        return TypeError(f"{cls.__name__} was built with refused data: {InvariantViolation.from_error(exc)}")

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """Enforce a flat hierarchy: a concrete output, or a class nested in one, extends UseCaseOutput directly."""
        super().__pydantic_init_subclass__(**kwargs)
        enforce_max_depth(cls, UseCaseOutput, 1)
