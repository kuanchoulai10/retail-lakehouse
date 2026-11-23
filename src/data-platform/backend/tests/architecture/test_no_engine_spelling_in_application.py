"""Guard that the application decides what maintenance does and leaves its call format to the adapters.

Iceberg's procedure option names, Spark SQL text and the text form of a time are how a call is
written, not what it does, so only the Spark adapter writes them (ADR 0016). The guard flags, in
every context's ``application/``:

- an Iceberg ``rewrite_data_files`` option name (``min-input-files``), also one joined from pieces
  (``"min-input" + "-files"``, ``f"min-{x}-files"``), and field names turned into option names
  with ``.replace("_", "-")``;
- Spark SQL in a string, also in an f-string or a ``+`` join, matched without regard to case or
  spacing: a backtick (or ``chr(96)``), ``.system``, ``IS NULL``, a ``DATE '``, ``TIMESTAMP '`` or
  ``TIMESTAMP_NTZ '`` literal;
- a time written as text: ``isoformat`` or ``strftime`` named at all (called, passed on, or as a
  ``getattr`` string), a ``%`` format spec in an f-string, a ``format()`` call, and ``str()``,
  ``repr()`` or an f-string of a value named like a time (``now``, ``moment``, ``older_than``,
  ``since``, ``before``, ``cutoff``, ``timestamp``, ``at`` or ``..._at``);
- a function whose name holds ``procedure``, which spells a procedure's arguments.

Docstrings and other string statements are prose and are not scanned, and an error message (an
f-string under ``raise`` or assigned to ``msg``) may name a time. Table properties
(``write.target-file-size-bytes``) and snapshot summary keys (``added-data-files``) are Iceberg's
data, not a call, and are not flagged. A time is recognised by its name, since the guard reads
syntax, not types.
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

import pytest

from tests.architecture.contexts import BACKEND, context_dir, context_names

if TYPE_CHECKING:
    from collections.abc import Iterator
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
SPARK_SQL_MARKERS = (
    ("`", re.compile("`")),
    (".system.", re.compile(r"\.system\b", re.IGNORECASE)),
    ("IS NULL", re.compile(r"\bis\s+null\b", re.IGNORECASE)),
    ("DATE '", re.compile(r"\bdate\s*'", re.IGNORECASE)),
    ("TIMESTAMP '", re.compile(r"\btimestamp\s*'", re.IGNORECASE)),
    ("TIMESTAMP_NTZ '", re.compile(r"\btimestamp_ntz\s*'", re.IGNORECASE)),
)
TIME_TEXT_METHODS = frozenset({"isoformat", "strftime"})
TIME_NAME = re.compile(r"(^|_)(now|moment|older_than|since|before|cutoff|timestamp|at)$")
_HOLE = "\x00"


def _prose(tree: ast.Module) -> set[int]:
    """Return the ids of string statements: docstrings, and the attribute docstrings after an assignment."""
    return {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
    }


def _error_messages(tree: ast.Module) -> set[int]:
    """Return the ids of f-strings that make an error message: under ``raise``, or assigned to ``msg``."""
    roots: list[ast.AST] = [node for node in ast.walk(tree) if isinstance(node, ast.Raise)]
    roots += [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "msg" for t in node.targets)
    ]
    return {id(node) for root in roots for node in ast.walk(root) if isinstance(node, ast.JoinedStr)}


def _joined(node: ast.expr) -> str | None:
    """Return the text of an f-string or a ``+`` join of strings, a hole for each part not written out."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(_joined(value) or _HOLE for value in node.values)
    if isinstance(node, ast.FormattedValue):
        return _HOLE
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _joined(node.left), _joined(node.right)
        if left is None and right is None:
            return None
        return (left or _HOLE) + (right or _HOLE)
    return None


def _texts(tree: ast.Module, prose: set[int]) -> Iterator[tuple[int, str]]:
    """Yield each string the module writes, joined: constants, f-strings and the outermost ``+`` joins."""
    inner = {
        id(child)
        for node in ast.walk(tree)
        if isinstance(node, (ast.BinOp, ast.JoinedStr))
        for child in ast.iter_child_nodes(node)
    }
    for node in ast.walk(tree):
        if id(node) in prose or id(node) in inner or not isinstance(node, (ast.Constant, ast.JoinedStr, ast.BinOp)):
            continue
        text = _joined(node)
        if text is not None:
            yield node.lineno, text


def _names_an_option(text: str) -> str | None:
    """Return the option name ``text`` spells, its holes standing for any text, or None."""
    if _HOLE not in text:
        return text if text in ICEBERG_OPTION_NAMES else None
    parts = text.split(_HOLE)
    if not any(re.search("[a-z]", part) for part in parts):
        return None
    pattern = re.compile(".+".join(re.escape(part) for part in parts))
    return next((name for name in sorted(ICEBERG_OPTION_NAMES) if pattern.fullmatch(name)), None)


def _tail_name(node: ast.expr) -> str:
    """Return the last name an expression ends in: ``now`` for ``request.now`` or ``now()``."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _tail_name(node.func)
    if isinstance(node, ast.Subscript):
        return _tail_name(node.value)
    return ""


def _is_time(node: ast.expr) -> bool:
    return bool(TIME_NAME.search(_tail_name(node)))


def _call_spellings(node: ast.Call) -> Iterator[str]:
    """Yield what a call spells: a time as text, a backtick or option names from field names."""
    func = node.func
    if isinstance(func, ast.Name) and func.id == "format":
        yield "time written as text with format()"
    if isinstance(func, ast.Name) and func.id in {"str", "repr"} and node.args and _is_time(node.args[0]):
        yield f"time written as text with {func.id}()"
    if isinstance(func, ast.Name) and func.id == "chr" and node.args:
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and arg.value == ord("`"):
            yield "Spark SQL '`' written with chr(96)"
    if isinstance(func, ast.Attribute) and func.attr == "replace" and len(node.args) == 2:
        values = [arg.value for arg in node.args if isinstance(arg, ast.Constant)]
        if values == ["_", "-"]:
            yield "Iceberg option names spelled with replace('_', '-')"


def engine_spellings(source: str) -> list[tuple[int, str]]:
    """Return ``(line, what)`` for each piece of a call's spelling in ``source``."""
    tree = ast.parse(source)
    prose = _prose(tree)
    messages = _error_messages(tree)
    found: list[tuple[int, str]] = []
    for line, text in _texts(tree, prose):
        option = _names_an_option(text)
        if option is not None:
            found.append((line, f"Iceberg option name {option!r}"))
        shown = text.replace(_HOLE, "{}")
        found.extend(
            (line, f"Spark SQL {label!r} in {shown!r}") for label, marker in SPARK_SQL_MARKERS if marker.search(text)
        )
        if text in TIME_TEXT_METHODS:
            found.append((line, f"time written as text with {text}()"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in TIME_TEXT_METHODS:
            found.append((node.lineno, f"time written as text with {node.attr}()"))
        elif isinstance(node, ast.Call):
            found.extend((node.lineno, what) for what in _call_spellings(node))
        elif isinstance(node, ast.JoinedStr):
            for value in node.values:
                if not isinstance(value, ast.FormattedValue):
                    continue
                spec = _joined(value.format_spec) if value.format_spec is not None else None
                if spec is not None and "%" in spec:
                    found.append((node.lineno, "time written as text with a format spec"))
                elif id(node) not in messages and _is_time(value.value):
                    found.append((node.lineno, "time written as text in an f-string"))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and "procedure" in node.name:
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


@pytest.mark.parametrize(
    "snippet",
    [
        pytest.param("def _procedure_options(self): pass", id="private-procedure-function"),
        pytest.param("def iceberg_procedure_args(job): pass", id="procedure-inside-a-name"),
        pytest.param("TEXT = str(now)", id="str-of-a-time"),
        pytest.param('TEXT = f"{now}"', id="f-string-of-a-value"),
        pytest.param('TEXT = f"{now:%Y-%m-%d %H:%M:%S}"', id="f-string-format-spec"),
        pytest.param('TEXT = format(now, "%Y")', id="format-call"),
        pytest.param("fmt = datetime.strftime", id="strftime-not-called"),
        pytest.param('TEXT = getattr(now, "isoformat")()', id="isoformat-by-getattr"),
        pytest.param('NAMES = {k.replace("_", "-"): v for k, v in options.items()}', id="underscores-to-hyphens"),
        pytest.param('KEY = "min-input" + "-files"', id="joined-option-name"),
        pytest.param('KEY = f"min-{x}-files"', id="f-string-option-name"),
        pytest.param('WHERE = f"{c} is null"', id="lowercase-is-null"),
        pytest.param("DAY = \"DATE'2026-01-01'\"", id="date-literal-without-space"),
        pytest.param("AT = \"timestamp '2026-01-01 00:00:00'\"", id="lowercase-timestamp-literal"),
        pytest.param("TICK = chr(96)", id="backtick-by-chr"),
        pytest.param('CALL = catalog + ".system" + ".bucket"', id="system-namespace-joined"),
    ],
)
def test_the_detector_has_no_known_bypass(snippet: str):
    """The ways around each rule a review found are caught too."""
    assert engine_spellings(snippet) != []


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
