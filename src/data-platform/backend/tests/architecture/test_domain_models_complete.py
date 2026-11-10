"""Guard tests: every Pydantic domain model is fully defined and copies only through validation.

A field annotation whose type is imported only under ``TYPE_CHECKING``, or
an import cycle, leaves a Pydantic model "not fully defined": it imports
fine and fails only at its first construction. Importing every module of
each domain model and checking ``__pydantic_complete__`` finds that at test
time instead.

``model_copy(update=...)`` skips validation, so a changed copy could break
an invariant silently; the domain copies through ``base.validated_copy``.
"""

from __future__ import annotations

import ast
import importlib
import pkgutil
from pathlib import Path

from pydantic import BaseModel

from tests.architecture.contexts import context_dir, context_module, context_names

BACKEND = Path(__file__).resolve().parents[2]


def _domain_model_classes() -> list[type[BaseModel]]:
    found: list[type[BaseModel]] = []
    for name in context_names():
        package = importlib.import_module(f"{context_module(name)}.application.domain.model")
        modules = [package.__name__]
        modules += [info.name for info in pkgutil.walk_packages(package.__path__, prefix=f"{package.__name__}.")]
        for module_name in modules:
            module = importlib.import_module(module_name)
            found.extend(
                value
                for value in vars(module).values()
                if isinstance(value, type) and issubclass(value, BaseModel) and value.__module__ == module_name
            )
    return found


def model_copy_calls(source: str) -> list[int]:
    """Return the line numbers of ``.model_copy(`` calls in ``source``."""
    return [
        node.lineno
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "model_copy"
    ]


def test_domain_models_are_complete() -> None:
    """Every Pydantic model in a domain model package is fully defined at import."""
    incomplete = [
        f"{cls.__module__}.{cls.__qualname__}" for cls in _domain_model_classes() if not cls.__pydantic_complete__
    ]
    assert incomplete == [], "not fully defined:\n" + "\n".join(incomplete)


def test_domain_never_calls_model_copy() -> None:
    """No domain module copies a model without validation."""
    violations = [
        f"{path.relative_to(BACKEND)}:{line}"
        for name in context_names()
        for path in sorted((context_dir(name) / "application" / "domain").rglob("*.py"))
        for line in model_copy_calls(path.read_text())
    ]
    assert violations == [], "use base.validated_copy instead of model_copy:\n" + "\n".join(violations)


def test_model_copy_scan_finds_a_call() -> None:
    """The scan flags a ``model_copy`` call."""
    assert model_copy_calls("x = settings.model_copy(update={'a': 1})\n") == [1]
