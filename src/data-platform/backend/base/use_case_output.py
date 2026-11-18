"""Define the Pydantic UseCaseOutput base class."""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict

from base._inheritance_guard import enforce_max_depth
from base._invariant_guarded_model import InvariantGuardedModel


class UseCaseOutput(InvariantGuardedModel):
    """The result an inbound port returns.

    Strict (a service passes the declared type: a ``tuple`` for a ``tuple``
    field), frozen, and unknown keys refused. Building one with refused data
    raises ``InvariantViolation``; assigning to a field raises
    ``AttributeError``.

    Fields hold primitives and standard-library types only (``str``, ``int``,
    ``float``, ``bool``, ``None``, ``datetime``, ``timedelta``, ``list``,
    ``tuple``, ``dict``) and classes nested one level inside the output, each
    extending ``UseCaseOutput`` directly and named by what it holds; never a
    domain type, so adapters never see the domain.

    Usage::

        class ListTableCommitsUseCaseOutput(UseCaseOutput):
            class Commit(UseCaseOutput):
                snapshot_id: int

            items: tuple[Commit, ...]
            truncated: bool
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """Enforce a flat hierarchy: a concrete output, or a class nested in one, extends UseCaseOutput directly."""
        super().__pydantic_init_subclass__(**kwargs)
        enforce_max_depth(cls, UseCaseOutput, 1)
