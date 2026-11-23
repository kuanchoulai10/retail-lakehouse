"""Guard that the application decides what maintenance does and leaves its call format to the adapters.

Iceberg's procedure option names, Spark SQL text and the text form of a time are how a call is
written, not what it does, so only the Spark adapter writes them (ADR 0016). The guard flags, in
every context's ``application/``:

- a string constant equal to an Iceberg ``rewrite_data_files`` option name (``min-input-files``),
- a string constant holding Spark SQL (a backtick, ``.system.``, `` IS NULL``, a ``DATE '`` or
  ``TIMESTAMP '`` literal),
- a call of ``isoformat`` or ``strftime``, which writes a time as text,
- a function named ``procedure_...``, which spells a procedure's arguments.

Docstrings and other string statements are prose and are not scanned. Table properties
(``write.target-file-size-bytes``) and snapshot summary keys (``added-data-files``) are Iceberg's
data, not a call, and are not flagged.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import pytest

from tests.architecture.contexts import BACKEND, context_dir, context_names

if TYPE_CHECKING:
    from pathlib import Path

ICEBERG_OPTION_NAMES = frozenset(
    {
        "target-file-size-bytes",
        "min-input-files",
        "min-file-size-bytes",
        "max-file-size-bytes",
        "partial-progress.enabled",
        "partial-progress.max-commits",
        "partial-progress.max-failed-commits",
        "max-concurrent-file-group-rewrites",
        "rewrite-all",
        "rewrite-job-order",
        "use-starting-sequence-number",
        "delete-file-threshold",
        "delete-ratio-threshold",
        "remove-dangling-deletes",
        "max-file-group-size-bytes",
        "output-spec-id",
        "max-files-to-rewrite",
        "compression-factor",
        "shuffle-partitions-per-file",
    }
)
SPARK_SQL_MARKERS = ("`", ".system.", " IS NULL", "DATE '", "TIMESTAMP '", "TIMESTAMP_NTZ '")
TIME_TEXT_METHODS = frozenset({"isoformat", "strftime"})


def _prose(tree: ast.Module) -> set[int]:
    """Return the ids of string statements: docstrings, and the attribute docstrings after an assignment."""
    return {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
    }


def engine_spellings(source: str) -> list[tuple[int, str]]:
    """Return ``(line, what)`` for each piece of a call's spelling in ``source``."""
    tree = ast.parse(source)
    prose = _prose(tree)
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in prose:
            if node.value in ICEBERG_OPTION_NAMES:
                found.append((node.lineno, f"Iceberg option name {node.value!r}"))
            for marker in SPARK_SQL_MARKERS:
                if marker in node.value:
                    found.append((node.lineno, f"Spark SQL {marker.strip()!r} in {node.value!r}"))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in TIME_TEXT_METHODS:
                found.append((node.lineno, f"time written as text with {node.func.attr}()"))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("procedure_"):
            found.append((node.lineno, f"procedure argument spelling {node.name}()"))
    return found


def _violations(application: Path) -> list[str]:
    return [
        f"{path.relative_to(BACKEND)}:{line} {what}"
        for path in sorted(application.rglob("*.py"))
        for line, what in engine_spellings(path.read_text())
    ]


@pytest.mark.parametrize(
    ("snippet", "what"),
    [
        ('OPTIONS = {"min-input-files": 2}', "Iceberg option name 'min-input-files'"),
        ('KEY = "partial-progress.enabled"', "Iceberg option name 'partial-progress.enabled'"),
        ('WHERE = f"`{column}` = 1"', "Spark SQL '`'"),
        ('CALL = "iceberg.system.rewrite_data_files"', "Spark SQL '.system.'"),
        ('NULL = "x IS NULL"', "Spark SQL 'IS NULL'"),
        ("DAY = \"DATE '2026-01-01'\"", 'Spark SQL "DATE \'"'),
        ("AT = \"TIMESTAMP_NTZ '2026-01-01 00:00:00'\"", 'Spark SQL "TIMESTAMP_NTZ \'"'),
        ("TEXT = moment.isoformat()", "time written as text with isoformat()"),
        ('TEXT = moment.strftime("%Y")', "time written as text with strftime()"),
        ("def procedure_options(self): pass", "procedure argument spelling procedure_options()"),
    ],
)
def test_the_detector_flags_each_kind_of_call_spelling(snippet: str, what: str):
    """Each rule catches its own spelling."""
    assert [found for _, found in engine_spellings(snippet) if found.startswith(what)] != []


def test_the_detector_leaves_data_names_and_prose_alone():
    """Table properties, summary keys and docstrings are not a call's spelling."""
    source = '''
"""Module prose may say ``target-file-size-bytes`` and `CALL iceberg.system.x`."""
PROPERTY = "write.target-file-size-bytes"
SUMMARY = "added-data-files"
RETENTION = "history.expire.max-snapshot-age-ms"


LIMIT = 3
"""An attribute docstring with ``backticks`` and DATE '2026-01-01' is prose too."""


def f():
    """Prose with a `backtick` is fine."""
    return moment.astimezone(tz)
'''
    assert engine_spellings(source) == []


@pytest.mark.parametrize("context", context_names())
def test_application_leaves_the_call_spelling_to_the_adapters(context: str):
    """No application code writes Iceberg option names, Spark SQL or time text."""
    violations = _violations(context_dir(context) / "application")
    assert violations == [], "\n".join(violations)
