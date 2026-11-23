"""Workflow modules must not use non-deterministic or client/worker APIs.

Temporal replays workflow code, so wall-clock time, randomness, UUIDs and the
client or worker APIs are off limits; workflows use ``workflow.now()``,
``workflow.random()``, ``workflow.uuid4()`` and activities instead. A workflow
takes the ids it needs from the application through local activities, since an
id type's ``new()`` mints from ``uuid.uuid7()`` (docs/adr/0015).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.architecture.contexts import context_dir, context_names

_WORKFLOWS = Path("adapter") / "hybrid" / "temporal" / "inbound" / "workflows"
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
            else:
                found += [
                    f"from {node.module} import {a.name}"
                    for a in node.names
                    if _is_forbidden(f"{node.module}.{a.name}")
                ]
        elif isinstance(node, ast.Attribute):
            owner = _rightmost_name(node.value)
            if owner in clock_names and node.attr in _CLOCK_METHODS:
                found.append(f"{owner}.{node.attr}")
    return found


def _workflow_modules(context_root: Path) -> list[Path]:
    return sorted((context_root / _WORKFLOWS).glob("*.py"))


def _has_temporal(context_root: Path) -> bool:
    return (context_root / "adapter" / "hybrid" / "temporal").is_dir()


def workflow_modules_missing(context_root: Path) -> bool:
    """Return True when the context has a Temporal adapter but no workflow module to check."""
    return _has_temporal(context_root) and not _workflow_modules(context_root)


@pytest.mark.parametrize("context", context_names())
def test_workflow_modules_are_found(context: str):
    """Each context with a Temporal adapter yields at least one workflow module to check."""
    assert not workflow_modules_missing(context_dir(context))


def test_workflow_modules_found_when_temporal_present(tmp_path: Path):
    """The check is skipped without a Temporal adapter and fails when it holds no workflow."""
    assert not workflow_modules_missing(tmp_path)
    (tmp_path / "adapter" / "hybrid" / "temporal").mkdir(parents=True)
    assert workflow_modules_missing(tmp_path)
    workflows = tmp_path / _WORKFLOWS
    workflows.mkdir(parents=True)
    (workflows / "a_workflow.py").write_text("")
    assert not workflow_modules_missing(tmp_path)


@pytest.mark.parametrize(
    "path",
    [path for context in context_names() for path in _workflow_modules(context_dir(context))],
    ids=lambda p: f"{p.parents[5].name}/{p.name}",
)
def test_workflow_module_is_deterministic(path: Path):
    """A workflow module contains no forbidden non-deterministic call."""
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
    """The checker reports each known non-deterministic source snippet."""
    assert violations(source) != []


def test_checker_accepts_workflow_apis():
    """The checker accepts the deterministic workflow replacements."""
    source = "from temporalio import workflow\nfrom datetime import timedelta\n"
    assert violations(source) == []


_PATCH_CALLS = ("patched", "deprecate_patch")


def patch_calls(source: str) -> list[str]:
    """Return each ``workflow.patched`` or ``workflow.deprecate_patch`` call in ``source``.

    Histories are not replayed across a change (the cluster is rebuilt instead), so a workflow keeps no
    branch for a history an older program wrote.
    """
    return [
        f"{_rightmost_name(node.func.value)}.{node.func.attr}"
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in _PATCH_CALLS
    ]


@pytest.mark.parametrize(
    "path",
    [path for context in context_names() for path in _workflow_modules(context_dir(context))],
    ids=lambda p: f"{p.parents[5].name}/{p.name}",
)
def test_no_workflow_calls_patched(path: Path):
    """A workflow module keeps no patch branch for an older history."""
    assert patch_calls(path.read_text()) == []


@pytest.mark.parametrize(
    "source",
    [
        "from temporalio import workflow\nif workflow.patched('p'):\n    pass",
        "from temporalio import workflow\nx = workflow.patched('p') and True",
        "from temporalio import workflow\nworkflow.deprecate_patch('p')",
    ],
)
def test_patch_checker_flags_patch_calls(source: str):
    """The patch checker reports a ``patched`` or ``deprecate_patch`` call wherever it stands."""
    assert patch_calls(source) != []


def test_patch_checker_accepts_other_workflow_calls():
    """The patch checker leaves other workflow calls and a name merely spelled ``patched`` alone."""
    assert patch_calls("from temporalio import workflow\npatched = True\nworkflow.now()\n") == []
