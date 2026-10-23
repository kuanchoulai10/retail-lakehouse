"""Workflow modules must not use non-deterministic or client/worker APIs.

Temporal replays workflow code, so wall-clock time, randomness, UUIDs and the
client or worker APIs are off limits; workflows use ``workflow.now()``,
``workflow.random()``, ``workflow.uuid4()`` and activities instead.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_WORKFLOWS = (
    Path(__file__).resolve().parents[2]
    / "adapter"
    / "inbound"
    / "temporal"
    / "workflows"
)
_FORBIDDEN_MODULES = (
    "time",
    "random",
    "uuid",
    "secrets",
    "threading",
    "temporalio.client",
    "temporalio.worker",
)
_CLOCK_CLASSES = ("datetime", "date")
_CLOCK_METHODS = ("now", "utcnow", "today")


def _is_forbidden(module: str) -> bool:
    return any(module == m or module.startswith(f"{m}.") for m in _FORBIDDEN_MODULES)


def _rightmost_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _clock_aliases(tree: ast.Module) -> set[str]:
    """Return the local names bound to ``datetime.datetime`` or ``datetime.date``."""
    return {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "datetime"
        for alias in node.names
        if alias.name in _CLOCK_CLASSES
    }


def violations(source: str) -> list[str]:
    """Return a description of every forbidden import or clock call in ``source``."""
    tree = ast.parse(source)
    clock_names = set(_CLOCK_CLASSES) | _clock_aliases(tree)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [f"import {a.name}" for a in node.names if _is_forbidden(a.name)]
        elif isinstance(node, ast.ImportFrom) and node.module:
            if _is_forbidden(node.module):
                found.append(f"from {node.module} import ...")
            elif node.module == "temporalio":
                found += [
                    f"from temporalio import {a.name}"
                    for a in node.names
                    if _is_forbidden(f"temporalio.{a.name}")
                ]
        elif isinstance(node, ast.Attribute):
            owner = _rightmost_name(node.value)
            if owner in clock_names and node.attr in _CLOCK_METHODS:
                found.append(f"{owner}.{node.attr}")
    return found


@pytest.mark.parametrize("path", sorted(_WORKFLOWS.glob("*.py")), ids=lambda p: p.name)
def test_workflow_module_is_deterministic(path: Path):
    assert violations(path.read_text()) == []


@pytest.mark.parametrize(
    "source",
    [
        "import time",
        "import random",
        "from uuid import uuid4",
        "from temporalio.client import Client",
        "from temporalio import worker",
        "import temporalio.worker",
        "from datetime import datetime\nx = datetime.now()",
        "import datetime\nx = datetime.datetime.utcnow()",
        "from datetime import datetime\nx = datetime.today()",
        "from datetime import datetime as dt\nx = dt.now()",
        "import datetime as d\nx = d.date.today()",
    ],
)
def test_checker_flags_forbidden_source(source: str):
    assert violations(source) != []


def test_checker_accepts_workflow_apis():
    source = "from temporalio import workflow\nfrom datetime import timedelta\n"
    assert violations(source) == []
