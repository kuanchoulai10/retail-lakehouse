"""Load the input and output models an inbound port use case defines."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from base import UseCaseInput, UseCaseOutput
from tests.architecture.contexts import context_module
from tests.architecture.inbound_ports import INBOUND_PORT_ROOTS, use_case_dirs

if TYPE_CHECKING:
    from pydantic import BaseModel


def port_models(key: str) -> list[type[BaseModel]]:
    """Return the top-level input and output models defined by the use case ``key``."""
    context, aggregate, use_case = key.split("/")
    package = ".".join([context_module(context), *INBOUND_PORT_ROOTS, aggregate, use_case])
    models: list[type[BaseModel]] = []
    for file_name, base in (("input", UseCaseInput), ("output", UseCaseOutput)):
        if not (use_case_dirs()[key] / f"{file_name}.py").is_file():
            continue
        module = importlib.import_module(f"{package}.{file_name}")
        models.extend(
            value
            for value in vars(module).values()
            if isinstance(value, type) and issubclass(value, base) and value.__module__ == module.__name__
        )
    return models
