"""The domain and the DDD kernel may import only the stdlib, base, their own domain and Pydantic."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from tests.architecture.contexts import context_names

BACKEND = Path(__file__).resolve().parents[2]
ALLOWED_THIRD_PARTY = {"pydantic", "pydantic_core", "annotated_types"}
ALLOWED_TOP_LEVEL = set(sys.stdlib_module_names) | {"__future__", "base"} | ALLOWED_THIRD_PARTY


def _imported_modules(tree: ast.AST) -> list[tuple[str, int]]:
    modules: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend((alias.name, 0) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.append((node.module or "", node.level))
    return modules


def disallowed_imports(source: str, context: str | None = None) -> list[str]:
    """Return the imported modules in ``source`` that the domain allow-list rejects."""
    own_domain = f"context.{context}.application.domain" if context else None
    violations: list[str] = []
    for module, level in _imported_modules(ast.parse(source)):
        if level:
            continue
        if module.split(".")[0] in ALLOWED_TOP_LEVEL:
            continue
        if own_domain and (module == own_domain or module.startswith(f"{own_domain}.")):
            continue
        violations.append(module)
    return violations


def _domain_files() -> list[tuple[Path, str | None]]:
    files: list[tuple[Path, str | None]] = [(p, None) for p in sorted((BACKEND / "base").rglob("*.py"))]
    for name in context_names():
        domain = BACKEND / "context" / name / "application" / "domain"
        files.extend((p, name) for p in sorted(domain.rglob("*.py")))
    return files


def test_domain_imports_only_allowed_modules():
    """No file in base or a domain imports outside the allow-list."""
    violations = [
        f"{path.relative_to(BACKEND)}: {module}"
        for path, context in _domain_files()
        for module in disallowed_imports(path.read_text(), context)
    ]
    assert violations == [], "\n".join(violations)


def test_allow_list_rejects_a_third_party_import():
    """The checker flags a third-party import."""
    assert disallowed_imports("import httpx\n") == ["httpx"]


def test_allow_list_accepts_pydantic():
    """The checker accepts Pydantic."""
    assert disallowed_imports("from pydantic import BaseModel\n") == []
