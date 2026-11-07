"""Guard test: bounded contexts do not reach into each other.

Context A may use context B only from A's outbound adapters (``adapter/outbound/``
or ``adapter/hybrid/<tech>/outbound/``), and only through B's inbound ports. A's application never imports another context, and ``base``
imports no context. ``bootstrap`` wires every context and is not checked.

import-linter wildcards cannot say "another context", so this rule is an AST
check. Imports under ``TYPE_CHECKING`` count, and relative imports are resolved
against the importing file's package before the same rules apply.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.contexts import BACKEND

CONTEXT_PACKAGE = "context"
ADAPTER = "adapter"
OUTBOUND = "outbound"
HYBRID = "hybrid"
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


def _package_parts(relative: Path) -> list[str]:
    """Return the dotted parts of the package a module file resolves imports in."""
    parts = list(relative.with_suffix("").parts)
    parts.pop()
    return parts


def _resolve(node: ast.ImportFrom, package: list[str]) -> str | None:
    """Return the absolute module of ``from <dots><module> import``, or None above the root."""
    if not node.level:
        return node.module
    keep = len(package) - (node.level - 1)
    if keep < 1:
        return None
    return ".".join([*package[:keep], *([node.module] if node.module else [])])


def _imported_modules(path: Path, backend: Path) -> list[tuple[int, str, bool]]:
    """Return (line, target, resolved) for every import in ``path``.

    Relative imports are resolved against the file's package. One that climbs
    above the top package it starts in (``context`` for a context file) is
    not resolved: its target is its relative spelling and it always counts.
    """
    package = _package_parts(path.relative_to(backend))
    found: list[tuple[int, str, bool]] = []
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if isinstance(node, ast.Import):
            found += [(node.lineno, alias.name, True) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            module = _resolve(node, package)
            if module is None:
                spelling = "." * node.level + (node.module or "")
                found.append((node.lineno, f"{spelling} climbs above context", False))
                continue
            found += [
                (node.lineno, f"{module}.{alias.name}", True) for alias in node.names
            ]
    return found


def _within(target: str, package: str) -> bool:
    return target == package or target.startswith(f"{package}.")


def _target_context(target: str) -> str | None:
    parts = target.split(".")
    if parts[0] != CONTEXT_PACKAGE or len(parts) < 2:
        return None
    return parts[1]


def _in_outbound_adapter(parts: tuple[str, ...]) -> bool:
    """Return whether ``context/<own>/...`` parts sit under an outbound adapter side."""
    side = parts[2:]
    if side[:2] == (ADAPTER, OUTBOUND):
        return len(side) > 2
    return len(side) > 4 and side[:2] == (ADAPTER, HYBRID) and side[3] == OUTBOUND


def _reaches_into(own: str, in_outbound: bool, target: str) -> bool:
    other = _target_context(target)
    if other is None or other == own:
        return False
    if not in_outbound:
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
        in_outbound = _in_outbound_adapter(parts)
        found += [
            f"{relative}:{line} {target}"
            for line, target, resolved in _imported_modules(path, backend)
            if not resolved or _reaches_into(own, in_outbound, target)
        ]
    for path in _python_files(backend / "base"):
        relative = path.relative_to(backend)
        found += [
            f"{relative}:{line} {target}"
            for line, target, resolved in _imported_modules(path, backend)
            if not resolved or _within(target, CONTEXT_PACKAGE)
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
        "context/alpha/adapter/outbound/port_ok.py": (
            "from context.beta.application.port import inbound\n"
        ),
        "context/alpha/adapter/outbound/whole.py": "from context import beta\n",
        "context/alpha/application/rel.py": (
            "from ...beta.application.domain.model import thing\n"
        ),
        "context/alpha/adapter/outbound/rel_ok.py": (
            "from ....beta.application.port.inbound import X\n"
        ),
        "context/alpha/application/up.py": "from .... import beta\n",
        "context/alpha/application/own_rel.py": "from .service import s\n",
        "context/alpha/adapter/__init__.py": (
            "from ...beta.application.domain import model\n"
        ),
        "context/alpha/adapter/inbound/web/uses_port.py": (
            "from context.beta.application.port.inbound import GetThingUseCase\n"
        ),
        "context/alpha/adapter/hybrid/temporal/inbound/act.py": (
            "from context.beta.application.port.inbound import GetThingUseCase\n"
        ),
        "context/alpha/adapter/hybrid/temporal/contracts/c.py": (
            "from context.beta.application.port.inbound import GetThingUseCase\n"
        ),
        "context/alpha/adapter/hybrid/temporal/outbound/thing/g.py": (
            "from context.beta.application.port.inbound import GetThingUseCase\n"
        ),
        "context/beta/application/domain/model/thing.py": "class Thing: ...\n",
        "base/b.py": "import context.alpha\n",
    }
    for relative, source in files.items():
        _write(tmp_path, relative, source)

    violations = cross_context_violations(tmp_path)

    assert sorted(violations) == sorted(
        [
            "context/alpha/application/service/s.py:1 "
            "context.beta.application.domain.model.thing.Thing",
            "context/alpha/adapter/outbound/bad.py:1 "
            "context.beta.application.port.outbound.ThingRepo",
            "context/alpha/adapter/inbound/web/w.py:3 "
            "context.beta.adapter.outbound.ThingSqlRepo",
            "context/alpha/adapter/outbound/whole.py:1 context.beta",
            "context/alpha/application/rel.py:1 "
            "context.beta.application.domain.model.thing",
            "context/alpha/application/up.py:1 .... climbs above context",
            "context/alpha/adapter/__init__.py:1 context.beta.application.domain.model",
            "context/alpha/adapter/inbound/web/uses_port.py:1 "
            "context.beta.application.port.inbound.GetThingUseCase",
            "context/alpha/adapter/hybrid/temporal/inbound/act.py:1 "
            "context.beta.application.port.inbound.GetThingUseCase",
            "context/alpha/adapter/hybrid/temporal/contracts/c.py:1 "
            "context.beta.application.port.inbound.GetThingUseCase",
            "base/b.py:1 context.alpha",
        ]
    )
