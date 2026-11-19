"""The shared kernel imports only the standard library and itself."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
SHARED_KERNEL = BACKEND / "shared_kernel"
ALLOWED_TOP_LEVEL = set(sys.stdlib_module_names) | {"__future__", "shared_kernel"}


def non_stdlib_imports(source: str) -> list[str]:
    """Return the absolute imports in ``source`` that name neither the stdlib nor the shared kernel."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.append("." * node.level + (node.module or ""))
    return [module for module in found if module.split(".")[0] not in ALLOWED_TOP_LEVEL]


def test_shared_kernel_imports_only_the_stdlib():
    """No module under shared_kernel imports a third-party or another project package."""
    violations = [
        f"{path.relative_to(BACKEND)}: {module}"
        for path in sorted(SHARED_KERNEL.rglob("*.py"))
        for module in non_stdlib_imports(path.read_text())
    ]
    assert violations == [], "\n".join(violations)


def test_the_checker_rejects_project_and_third_party_imports():
    """The checker flags a base, a Pydantic and a relative import."""
    source = "import pydantic\nfrom base import EntityId\nfrom . import sibling\nimport re\n"

    assert non_stdlib_imports(source) == ["pydantic", "base", "."]
