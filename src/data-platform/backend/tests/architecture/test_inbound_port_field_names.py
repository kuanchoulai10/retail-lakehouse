"""Guard test: no field of a migrated inbound port model is named like an attribute of ``pydantic.BaseModel``.

A field called ``schema``, ``json``, ``copy``, ``dict``, ``validate`` or ``construct`` shadows a ``BaseModel``
attribute: Pydantic warns when the module is loaded, and a mapper that reads the attribute gets the method.
Name the field by what it holds instead (``table_schema``, ``view_schema``). The check covers every class a
migrated ``input.py`` / ``output.py`` defines, nested classes included.
"""

from __future__ import annotations

import importlib
import warnings

import pytest
from pydantic import BaseModel

from base import UseCaseInput, UseCaseOutput
from tests.architecture.contexts import context_module
from tests.architecture.test_inbound_port_models import INBOUND_PORT, _all_use_case_dirs, _migrated

BASE_MODEL_ATTRIBUTES = frozenset(dir(BaseModel))


def shadowing_fields(model: type[BaseModel]) -> list[str]:
    """Return the field names of ``model``, and of the models nested in it, that are ``BaseModel`` attributes."""
    found = sorted(set(model.model_fields) & BASE_MODEL_ATTRIBUTES)
    problems = [f"{model.__name__}.{name}" for name in found]
    for nested in vars(model).values():
        if isinstance(nested, type) and issubclass(nested, BaseModel):
            problems.extend(f"{model.__name__}.{problem}" for problem in shadowing_fields(nested))
    return problems


def _port_models(key: str) -> list[type[BaseModel]]:
    """Return the top-level input and output models defined by the use case ``key``."""
    context, aggregate, use_case = key.split("/")
    package = ".".join([context_module(context), *INBOUND_PORT, aggregate, use_case])
    models: list[type[BaseModel]] = []
    for file_name, base in (("input", UseCaseInput), ("output", UseCaseOutput)):
        if not (_all_use_case_dirs()[key] / f"{file_name}.py").is_file():
            continue
        module = importlib.import_module(f"{package}.{file_name}")
        models.extend(
            value
            for value in vars(module).values()
            if isinstance(value, type) and issubclass(value, base) and value.__module__ == module.__name__
        )
    return models


def test_the_scan_finds_models_to_check() -> None:
    """The migrated use cases yield models, so a pass means something."""
    assert sum(len(_port_models(key)) for key in _migrated()) > 0


@pytest.mark.parametrize("key", _migrated())
def test_no_port_field_shadows_a_base_model_attribute(key: str) -> None:
    """Every field of a migrated input or output, and of its nested classes, has a name ``BaseModel`` lacks."""
    problems = [problem for model in _port_models(key) for problem in shadowing_fields(model)]
    assert problems == [], f"{key} has fields that shadow a pydantic.BaseModel attribute: {problems}"


def test_the_checker_reports_a_shadowing_field_on_a_nested_class() -> None:
    """A field named ``schema`` on the output, or ``json`` on a nested class, is reported."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)

        class GetWidgetUseCaseOutput(UseCaseOutput):
            class Part(UseCaseOutput):
                json: str

            name: str
            schema: dict[str, str]
            parts: tuple[Part, ...]

    assert shadowing_fields(GetWidgetUseCaseOutput) == [
        "GetWidgetUseCaseOutput.schema",
        "GetWidgetUseCaseOutput.Part.json",
    ]


def test_the_checker_accepts_names_by_what_they_hold() -> None:
    """``table_schema`` is not a ``BaseModel`` attribute, so it passes."""

    class GetWidgetUseCaseOutput(UseCaseOutput):
        widget_schema: dict[str, str]

    assert shadowing_fields(GetWidgetUseCaseOutput) == []
