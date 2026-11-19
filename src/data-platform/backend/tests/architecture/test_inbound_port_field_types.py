"""Guard test: every field of an inbound port model holds an allowed type.

A port field holds ``str``, ``int``, ``float``, ``bool``, ``None``, ``datetime``, ``timedelta``, a ``Literal``,
a ``tuple[...]`` or ``dict[...]`` of allowed types, a class nested in the same port file, or an optional or union
of these. ``Any`` is allowed only inside a ``dict`` or ``tuple`` (a structured blob the application passes
through). ``list`` and ``set`` are refused: a sequence is a ``tuple``. Anything else (an enum, a domain type, a
type from an outbound port) is refused, so adapters never see the domain. The check covers every field of every
input and output, nested classes included.
"""

from __future__ import annotations

import sys
import types
import typing
from datetime import datetime, timedelta
from typing import Any, Literal

import pytest
from pydantic import BaseModel

from base import UseCaseInput, UseCaseOutput
from tests.architecture.inbound_port_models import port_models
from tests.architecture.inbound_ports import use_case_dirs

_SCALARS: frozenset[object] = frozenset({str, int, float, bool, type(None), datetime, timedelta})
_REFUSED_SEQUENCES = {list: "list", set: "set", frozenset: "frozenset"}
_FOREIGN = "not a primitive, a tuple, a dict or a class nested in the port"


class _Port:
    """A port model and the classes nested in it, which resolves the forward references its nested classes keep.

    A nested class naming a sibling (``tuple[Output.Measurement, ...]``) keeps it as a ``ForwardRef`` in its own
    ``model_fields`` until Pydantic rebuilds it; it is resolved here in the port module's namespace.
    """

    def __init__(self, model: type[BaseModel]) -> None:
        self.model = model
        self.nested = tuple(
            value for value in vars(model).values() if isinstance(value, type) and issubclass(value, BaseModel)
        )
        self._namespace = {
            **vars(sys.modules[model.__module__]),
            model.__name__: model,
            **{nested.__name__: nested for nested in self.nested},
        }

    def unwrap(self, annotation: object) -> object:
        """Return ``annotation`` with a forward reference resolved and ``Annotated`` metadata dropped."""
        if isinstance(annotation, typing.ForwardRef):
            annotation = eval(annotation.__forward_arg__, self._namespace)  # noqa: S307
        while typing.get_origin(annotation) is typing.Annotated:
            annotation = typing.get_args(annotation)[0]
        return annotation


def _type_name(annotation: object) -> str:
    if annotation is Any:
        return "Any"
    if isinstance(annotation, type) and typing.get_origin(annotation) is None:
        return annotation.__qualname__
    return repr(annotation).replace("typing.", "")


def _leaf_problem(annotation: object, port: _Port, *, in_container: bool) -> str | None:
    """Return why a type that is neither a union, a tuple nor a dict may not be a port field, or ``None``."""
    origin = typing.get_origin(annotation)
    if annotation is Any:
        return None if in_container else "Any (Any is allowed only inside a dict or tuple)"
    if annotation in _SCALARS or annotation in port.nested or origin is Literal:
        return None
    if origin in _REFUSED_SEQUENCES:
        return f"{_type_name(annotation)} ({_REFUSED_SEQUENCES[origin]} is refused; a sequence is a tuple)"
    return f"{_type_name(annotation)} ({_FOREIGN})"


def _annotation_problems(annotation: object, port: _Port, *, in_container: bool) -> list[str]:
    """Return a ``"<type> (<why>)"`` line for each part of ``annotation`` a port field may not hold."""
    annotation = port.unwrap(annotation)
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if origin in (types.UnionType, typing.Union):
        inner, inside = args, in_container
    elif origin in (tuple, dict) and args:
        inner, inside = tuple(arg for arg in args if arg is not Ellipsis), True
    else:
        problem = _leaf_problem(annotation, port, in_container=in_container)
        return [] if problem is None else [problem]
    return [problem for arg in inner for problem in _annotation_problems(arg, port, in_container=inside)]


def port_field_type_problems(model: type[BaseModel]) -> list[str]:
    """Return each field of ``model``, or of a class nested in it, whose type a port field may not hold."""
    port = _Port(model)
    problems: list[str] = []
    for owner, prefix in [(model, model.__name__), *((n, f"{model.__name__}.{n.__name__}") for n in port.nested)]:
        for name, field in owner.model_fields.items():
            problems.extend(
                f"{prefix}.{name}: {problem}"
                for problem in _annotation_problems(field.annotation, port, in_container=False)
            )
    return problems


def test_the_scan_finds_fields_to_check() -> None:
    """The use cases yield models with fields, so a pass means something."""
    assert sum(len(model.model_fields) for key in sorted(use_case_dirs()) for model in port_models(key)) > 0


@pytest.mark.parametrize("key", sorted(use_case_dirs()))
def test_every_port_field_holds_an_allowed_type(key: str) -> None:
    """Every field of an input or output, and of its nested classes, holds an allowed type."""
    problems = [problem for model in port_models(key) for problem in port_field_type_problems(model)]
    assert problems == [], f"{key} has fields of types a port may not hold: {problems}"


class _Colour:
    """A class that is not a port field type (as a domain or outbound port type would be)."""


class _GoodUseCaseOutput(UseCaseOutput):
    """Every allowed shape."""

    class Sibling(UseCaseOutput):
        """A nested class another nested class holds."""

        weight: float

    class Part(UseCaseOutput):
        """A nested class, whose fields may name a sibling nested class."""

        name: str
        size: int | None
        siblings: tuple[_GoodUseCaseOutput.Sibling, ...]

    name: str
    count: int
    ratio: float
    active: bool
    note: None
    made_at: datetime
    took: timedelta
    kind: Literal["a", "b"]
    tags: tuple[str, ...]
    pair: tuple[int, str]
    labels: dict[str, str]
    blob: dict[str, Any]
    raw: tuple[Any, ...]
    parts: tuple[Part, ...]
    main: Part | None
    either: str | int


def test_checker_accepts_every_allowed_shape() -> None:
    """Primitives, Literal, tuples, dicts, Any inside them, nested classes and unions pass."""
    assert port_field_type_problems(_GoodUseCaseOutput) == []


class _BadUseCaseInput(UseCaseInput):
    """Every refused shape."""

    model_config = {"arbitrary_types_allowed": True}

    class Part(UseCaseInput):
        """A nested class with a refused field."""

        names: list[str]

    names: list[str]
    ids: set[int]
    anything: Any
    colour: _Colour
    maybe_colour: _Colour | None
    nested_list: tuple[list[str], ...]
    values: dict[str, set[str]]
    part: Part


def test_checker_reports_every_refused_shape() -> None:
    """``list``, ``set``, a bare ``Any`` and a foreign class are reported, at any depth and in a nested class."""
    assert port_field_type_problems(_BadUseCaseInput) == [
        "_BadUseCaseInput.names: list[str] (list is refused; a sequence is a tuple)",
        "_BadUseCaseInput.ids: set[int] (set is refused; a sequence is a tuple)",
        "_BadUseCaseInput.anything: Any (Any is allowed only inside a dict or tuple)",
        "_BadUseCaseInput.colour: _Colour (not a primitive, a tuple, a dict or a class nested in the port)",
        "_BadUseCaseInput.maybe_colour: _Colour (not a primitive, a tuple, a dict or a class nested in the port)",
        "_BadUseCaseInput.nested_list: list[str] (list is refused; a sequence is a tuple)",
        "_BadUseCaseInput.values: set[str] (set is refused; a sequence is a tuple)",
        "_BadUseCaseInput.Part.names: list[str] (list is refused; a sequence is a tuple)",
    ]


class _OtherUseCaseOutput(UseCaseOutput):
    """Another port, whose nested class the next port must not hold."""

    class Part(UseCaseOutput):
        """A class nested in another port."""

        name: str

    part: Part


class _BorrowingUseCaseOutput(UseCaseOutput):
    """A port that holds a class nested in another port."""

    part: _OtherUseCaseOutput.Part


def test_checker_reports_a_class_nested_in_another_port() -> None:
    """Only classes nested in the same port file count as nested classes."""
    assert port_field_type_problems(_BorrowingUseCaseOutput) == [
        "_BorrowingUseCaseOutput.part: _OtherUseCaseOutput.Part "
        "(not a primitive, a tuple, a dict or a class nested in the port)",
    ]
