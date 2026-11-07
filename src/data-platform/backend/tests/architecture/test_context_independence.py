"""Guard test: bounded contexts do not reach into each other.

Context A may use context B only from A's adapters, and only through B's
inbound ports. A's application never imports another context, and ``base``
imports no context. ``bootstrap`` wires every context and is not checked.

import-linter wildcards cannot say "another context", so this rule is an AST
check. Imports under ``TYPE_CHECKING`` count.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.contexts import BACKEND

CONTEXT_PACKAGE = "context"
ADAPTER = "adapter"
INBOUND_PORT = ("application", "port", "inbound")
SKIPPED_PARTS = {"__pycache__", ".venv"}


def _python_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(
        path
        for path in directory.rglob("*.py")
        if not SKIPPED_PARTS & set(path.relative_to(directory).parts)
    )


def _imported_modules(path: Path) -> list[tuple[int, str]]:
    """Return (line, dotted target) for every absolute import in ``path``."""
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if isinstance(node, ast.Import):
            found += [(node.lineno, alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            found += [
                (node.lineno, f"{node.module}.{alias.name}") for alias in node.names
            ]
    return found


def _within(target: str, package: str) -> bool:
    return target == package or target.startswith(f"{package}.")


def _target_context(target: str) -> str | None:
    parts = target.split(".")
    if parts[0] != CONTEXT_PACKAGE or len(parts) < 2:
        return None
    return parts[1]


def _reaches_into(own: str, in_adapter: bool, target: str) -> bool:
    other = _target_context(target)
    if other is None or other == own:
        return False
    if not in_adapter:
        return True
    return not _within(target, ".".join((CONTEXT_PACKAGE, other, *INBOUND_PORT)))


def cross_context_violations(backend: Path) -> list[str]:
    """Return ``"<path>:<line> <target>"`` for every import across a context line."""
    found: list[str] = []
    for path in _python_files(backend / CONTEXT_PACKAGE):
        relative = path.relative_to(backend)
        parts = relative.parts
        if len(parts) < 3:
            continue
        own = parts[1]
        in_adapter = parts[2] == ADAPTER
        found += [
            f"{relative}:{line} {target}"
            for line, target in _imported_modules(path)
            if _reaches_into(own, in_adapter, target)
        ]
    for path in _python_files(backend / "base"):
        relative = path.relative_to(backend)
        found += [
            f"{relative}:{line} {target}"
            for line, target in _imported_modules(path)
            if _within(target, CONTEXT_PACKAGE)
        ]
    return found


def test_contexts_do_not_reach_into_each_other():
    violations = cross_context_violations(BACKEND)
    assert violations == [], "\n".join(violations)


def _write(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)


def test_cross_context_import_rules(tmp_path: Path):
    files = {
        "context/alpha/application/service/s.py": (
            "from context.beta.application.domain.model.thing import Thing\n"
        ),
        "context/alpha/adapter/outbound/ok.py": (
            "from context.beta.application.port.inbound import GetThingUseCase\n"
        ),
        "context/alpha/adapter/outbound/bad.py": (
            "from context.beta.application.port.outbound import ThingRepo\n"
        ),
        "context/alpha/adapter/inbound/web/w.py": (
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n"
            "    from context.beta.adapter.outbound import ThingSqlRepo\n"
        ),
        "context/alpha/adapter/outbound/own.py": (
            "from context.alpha.application.domain.model import Widget\n"
        ),
        "context/beta/application/domain/model/thing.py": "class Thing: ...\n",
        "base/b.py": "import context.alpha\n",
    }
    for relative, source in files.items():
        _write(tmp_path, relative, source)

    violations = cross_context_violations(tmp_path)

    assert sorted(v.split(":")[0] for v in violations) == sorted(
        [
            "context/alpha/application/service/s.py",
            "context/alpha/adapter/outbound/bad.py",
            "context/alpha/adapter/inbound/web/w.py",
            "base/b.py",
        ]
    )
