"""Aggregate names of a context, derived from its domain model.

An aggregate is a child package of ``application/domain/model`` (except
``shared``) that defines a subclass of ``base.AggregateRoot``. The list comes
from the model, not from the directories of other layers, so a stray or
misspelt directory in another layer still fails the aggregate axis.
"""

from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType

from base import AggregateRoot
from tests.architecture.contexts import context_module

SHARED = "shared"


def _defines_aggregate_root(module: ModuleType) -> bool:
    return any(
        isinstance(value, type)
        and value.__module__ == module.__name__
        and issubclass(value, AggregateRoot)
        and value is not AggregateRoot
        for value in vars(module).values()
    )


def _modules_of(package: ModuleType) -> list[ModuleType]:
    modules = [package]
    for info in pkgutil.walk_packages(package.__path__, prefix=f"{package.__name__}."):
        modules.append(importlib.import_module(info.name))
    return modules


def derive_aggregates(model_package: str) -> set[str]:
    """Return the child packages of ``model_package`` that define an aggregate root."""
    model = importlib.import_module(model_package)
    found: set[str] = set()
    for info in pkgutil.iter_modules(model.__path__):
        if not info.ispkg or info.name == SHARED:
            continue
        package = importlib.import_module(f"{model_package}.{info.name}")
        if any(_defines_aggregate_root(module) for module in _modules_of(package)):
            found.add(info.name)
    return found


def aggregates(context: str) -> set[str]:
    """Return the aggregate names of ``context``."""
    return derive_aggregates(f"{context_module(context)}.application.domain.model")
