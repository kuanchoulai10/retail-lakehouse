"""Guard test: application/ names carry no infrastructure vocabulary."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from tests.architecture.contexts import BACKEND, context_dir, context_names


BANNED = {
    "temporal",
    "workflow",
    "signal",
    "activity",
    "spark",
    "k8s",
    "kubernetes",
    "sql",
    "pyiceberg",
    "iceberg_rest",
    "kafka",
    "polaris",
}


def tokenize(name: str) -> list[str]:
    """Split a name on ``_`` and camelCase boundaries, lower-cased."""
    spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", spaced)
    return [token.lower() for token in spaced.split("_") if token]


def banned_terms(name: str) -> set[str]:
    """Return the banned terms whose words appear as consecutive tokens of name."""
    tokens = tokenize(name)
    found: set[str] = set()
    for term in BANNED:
        words = term.split("_")
        joined = "".join(words)
        for start in range(len(tokens)):
            if tokens[start : start + len(words)] == words:
                found.add(term)
                break
            if any(
                "".join(tokens[start:end]) == joined
                for end in range(start + 1, len(tokens) + 1)
            ):
                found.add(term)
                break
    return found


def _target_names(target: ast.expr) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [name for elt in target.elts for name in _target_names(elt)]
    return []


def _assigned_names(body: list[ast.stmt]) -> list[tuple[int, str]]:
    names: list[tuple[int, str]] = []
    for stmt in body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                names += [(stmt.lineno, n) for n in _target_names(target)]
        elif isinstance(stmt, ast.AnnAssign):
            names += [(stmt.lineno, n) for n in _target_names(stmt.target)]
    return names


IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _docstrings(tree: ast.Module) -> set[int]:
    """Return the ids of the docstring constants of the module, classes and functions."""
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                found.add(id(body[0].value))
    return found


def _identifier_strings(tree: ast.Module) -> list[tuple[int, str]]:
    """Return the non-docstring ``str`` constants shaped like identifiers."""
    docstrings = _docstrings(tree)
    return [
        (node.lineno, node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
        and IDENTIFIER.match(node.value)
    ]


def _names_in(tree: ast.Module) -> list[tuple[int, str]]:
    names = _assigned_names(tree.body) + _identifier_strings(tree)
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            names.append((node.lineno, node.name))
        if isinstance(node, ast.ClassDef):
            names += _assigned_names(node.body)
        elif isinstance(node, ast.arg):
            names.append((node.lineno, node.arg))
        elif isinstance(node, ast.keyword) and node.arg is not None:
            names.append((node.lineno, node.arg))
        elif isinstance(node, ast.Attribute):
            names.append((node.lineno, node.attr))
    return names


def _violations(application: Path) -> list[str]:
    found: list[str] = []
    for path in sorted(application.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(BACKEND)
        found += [
            f"{rel}:0 {segment}"
            for segment in rel.with_suffix("").parts
            if banned_terms(segment)
        ]
        tree = ast.parse(path.read_text(), filename=str(path))
        found += [
            f"{rel}:{lineno} {name}"
            for lineno, name in _names_in(tree)
            if banned_terms(name)
        ]
    return sorted(set(found))


def test_banned_term_detector_catches_camel_and_snake():
    assert tokenize("needsReconcileWorkflow") == ["needs", "reconcile", "workflow"]
    assert tokenize("spark_application") == ["spark", "application"]
    assert tokenize("SIGNAL_STOP") == ["signal", "stop"]
    assert banned_terms("needsReconcileWorkflow") == {"workflow"}
    assert banned_terms("spark_application") == {"spark"}
    assert banned_terms("SIGNAL_STOP") == {"signal"}
    assert banned_terms("SparkK8sConfig") == {"spark", "k8s"}
    assert banned_terms("read_iceberg_rest_catalog") == {"iceberg_rest"}
    assert banned_terms("iceberg_table_rest") == set()
    assert banned_terms("PyIceberg") == {"pyiceberg"}
    assert banned_terms("pyIcebergCatalog") == {"pyiceberg"}
    assert banned_terms("py_iceberg_catalog") == {"pyiceberg"}
    assert banned_terms("iceberg_py") == set()
    assert banned_terms("PyTable") == set()


def test_identifier_strings_are_scanned_but_docstrings_and_prose_are_not():
    tree = ast.parse(
        '''"""Talk about the workflow."""
KIND = "spark_job"
LABEL = "a workflow step"


def f():
    """Signal the workflow."""
    return {"temporal": 1}
'''
    )
    assert sorted(v for _, v in _identifier_strings(tree)) == ["spark_job", "temporal"]


@pytest.mark.parametrize("context", context_names())
def test_application_names_have_no_infrastructure_terms(context: str):
    violations = _violations(context_dir(context) / "application")
    assert not violations, "Infrastructure terms in application/:\n" + "\n".join(
        violations
    )
