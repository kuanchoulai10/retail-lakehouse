"""Guard tests: code imports another package only through its boundary.

See ``tests/architecture/boundaries.py`` for how boundaries are derived.
"""

from __future__ import annotations

import ast
import importlib
import subprocess
import sys
import typing
from typing import TYPE_CHECKING

import pytest

from base import AggregateRoot, EntityId, Repository
from tests.architecture.aggregates import aggregates, derive_aggregates
from tests.architecture.boundaries import (
    BACKEND,
    PROJECT_PACKAGES,
    boundaries,
    innermost_boundary,
)
from tests.architecture.contexts import context_dir, context_module, context_names
from tests.architecture.fixture_context import build_fixture_context

if TYPE_CHECKING:
    from pathlib import Path

SCANNED_DIRS = (*PROJECT_PACKAGES, "tests")
SCANNED_FILES = ("entrypoint.py",)
SKIPPED_PARTS = {"__pycache__", ".venv"}


def _source_files() -> list[Path]:
    files = [BACKEND / name for name in SCANNED_FILES]
    for directory in SCANNED_DIRS:
        files.extend(
            path
            for path in (BACKEND / directory).rglob("*.py")
            if not SKIPPED_PARTS & set(path.relative_to(BACKEND).parts)
        )
    return sorted(files)


def _module_name(path: Path) -> str:
    parts = list(path.relative_to(BACKEND).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _module_path(module: str) -> Path | None:
    base = BACKEND.joinpath(*module.split("."))
    for candidate in (base.with_suffix(".py"), base / "__init__.py"):
        if candidate.is_file():
            return candidate
    return None


def _package_all(package: str) -> list[str]:
    """Return a package's ``__all__``; its names shadow same-named submodules."""
    init = BACKEND.joinpath(*package.split(".")) / "__init__.py"
    return (_declared_all(init) or []) if init.is_file() else []


def _is_project(module: str) -> bool:
    return module.split(".", 1)[0] in PROJECT_PACKAGES


def _import_targets(node: ast.Import | ast.ImportFrom) -> list[str]:
    """Return the project modules an import statement names."""
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names if _is_project(alias.name)]
    if node.module and _is_project(node.module):
        targets = []
        for alias in node.names:
            submodule = f"{node.module}.{alias.name}"
            is_submodule = _module_path(submodule) is not None
            if is_submodule and alias.name in _package_all(node.module):
                is_submodule = False
            targets.append(submodule if is_submodule else node.module)
        return targets
    return []


def _violations() -> list[str]:
    known = boundaries()
    found: list[str] = []
    for path in _source_files():
        own = innermost_boundary(_module_name(path), known)
        relative = path.relative_to(BACKEND)
        for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
            if not isinstance(node, ast.Import | ast.ImportFrom):
                continue
            if isinstance(node, ast.ImportFrom) and node.level:
                found.append(f"{relative}:{node.lineno} relative import is not allowed")
                continue
            for target in _import_targets(node):
                boundary = innermost_boundary(target, known)
                if boundary is None or boundary in (own, target):
                    continue
                found.append(f"{relative}:{node.lineno} {target} → expected {boundary}")
    return found


def test_no_import_past_a_boundary():
    """No module imports past the public entry point of a boundary package."""
    violations = _violations()
    assert not violations, f"{len(violations)} imports reach past a boundary:\n" + "\n".join(violations)


def _boundary_dir(boundary: str) -> Path:
    return BACKEND.joinpath(*boundary.split("."))


def _modules_below(boundary: str, known: set[str]) -> list[Path]:
    """Return the non-private modules of a boundary, outside its child boundaries."""
    modules: list[Path] = []
    pending = [_boundary_dir(boundary)]
    while pending:
        directory = pending.pop()
        for child in sorted(directory.iterdir()):
            if child.is_dir() and (child / "__init__.py").is_file():
                if _dotted_dir(child) not in known:
                    pending.append(child)
            elif child.suffix == ".py" and child.name != "__init__.py" and not child.name.startswith("_"):
                modules.append(child)
    return modules


def _dotted_dir(directory: Path) -> str:
    return ".".join(directory.relative_to(BACKEND).parts)


def _defined_names(tree: ast.Module) -> tuple[list[str], list[str]]:
    """Return the public (definitions, assigned names) at module level."""
    definitions: list[str] = []
    assigned: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            definitions.append(node.name)
        elif isinstance(node, ast.Assign):
            assigned.extend(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assigned.append(node.target.id)
        elif isinstance(node, ast.TypeAlias) and isinstance(node.name, ast.Name):
            assigned.append(node.name.id)

    def public(names: list[str]) -> list[str]:
        return [name for name in names if not name.startswith("_")]

    return public(definitions), public(assigned)


def _primary_exports(module: Path) -> list[str]:
    """Return the name matching the module, else its public definitions and constants."""
    definitions, assigned = _defined_names(ast.parse(module.read_text()))
    flat = module.stem.replace("_", "")
    primary = [name for name in definitions + assigned if name.lower().replace("_", "") == flat]
    if primary:
        return primary
    return definitions + [name for name in assigned if name.isupper()]


def _declared_all(init: Path) -> list[str] | None:
    for node in ast.parse(init.read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
            assert isinstance(node.value, ast.List | ast.Tuple)
            return [
                elt.value for elt in node.value.elts if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            ]
    return None


def test_boundary_all_is_complete():
    """Every boundary lists its public names in a complete __all__."""
    known = boundaries()
    problems: list[str] = []
    for boundary in sorted(known):
        declared = _declared_all(_boundary_dir(boundary) / "__init__.py")
        if declared is None:
            problems.append(f"{boundary}: __init__ defines no __all__")
            continue
        for module in _modules_below(boundary, known):
            missing = [n for n in _primary_exports(module) if n not in declared]
            if missing:
                relative = module.relative_to(BACKEND)
                problems.append(f"{boundary}: {relative} exports missing {missing}")
    assert not problems, "\n".join(problems)


def test_boundary_exports_are_unambiguous():
    """Two modules of one boundary must not export the same name: one would shadow the other."""
    known = boundaries()
    clashes: list[str] = []
    for boundary in sorted(known):
        owners: dict[str, list[str]] = {}
        for module in _modules_below(boundary, known):
            for name in _primary_exports(module):
                owners.setdefault(name, []).append(module.name)
        clashes.extend(
            f"{boundary}: {name} exported by {modules}" for name, modules in owners.items() if len(modules) > 1
        )
    assert not clashes, "\n".join(clashes)


def test_exports_do_not_shadow_a_sibling_module():
    """An exported name equal to a module of the boundary must be that module's own export.

    Otherwise importing that submodule rebinds the package attribute to the module
    object, depending on import order.
    """
    known = boundaries()
    problems: list[str] = []
    for boundary in sorted(known):
        directory = _boundary_dir(boundary)
        declared = _declared_all(directory / "__init__.py") or []
        for name in declared:
            module = directory / f"{name}.py"
            if module.is_file() and name not in _primary_exports(module):
                problems.append(f"{boundary}: {name} shadows module {module.name}")
    assert not problems, "\n".join(problems)


GLOBAL_BOUNDARIES = ("base", "bootstrap.configs", "bootstrap.container")
CONTEXT_KERNEL_BOUNDARIES = ("application.exceptions",)
AGGREGATE_BOUNDARY_LAYERS = (
    "application.domain.model",
    "application.port.inbound",
    "application.port.outbound",
)
STRUCTURAL_PACKAGES = (
    "application",
    "adapter",
    *AGGREGATE_BOUNDARY_LAYERS,
)


@pytest.mark.parametrize("context", context_names())
def test_boundaries_follow_the_directory_rules(context: str):
    """Only shapes every context has; concrete samples live in each context's tests."""
    known = boundaries()
    prefix = context_module(context)
    for expected in (
        *GLOBAL_BOUNDARIES,
        *(f"{prefix}.{suffix}" for suffix in CONTEXT_KERNEL_BOUNDARIES),
        *(
            f"{prefix}.{layer}.{aggregate}"
            for layer in AGGREGATE_BOUNDARY_LAYERS
            for aggregate in sorted(aggregates(context))
        ),
    ):
        assert expected in known, expected
    for not_a_boundary in (
        "bootstrap",
        "context",
        prefix,
        *(f"{prefix}.{package}" for package in STRUCTURAL_PACKAGES),
    ):
        assert not_a_boundary not in known, not_a_boundary


@pytest.mark.parametrize("boundary", sorted(boundaries()))
def test_every_boundary_imports_in_isolation(boundary: str):
    """Each boundary package imports in a fresh interpreter without circular import errors."""
    result = subprocess.run(
        [sys.executable, "-c", f"import {boundary}"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _generic_argument(cls: type, origin: type) -> type:
    """Return the type argument ``cls`` passes to the generic base ``origin``.

    A plain generic (``Repository``) records ``Base[Arg]`` in
    ``__orig_bases__``; a Pydantic generic (``AggregateRoot``) creates a real
    class ``Base[Arg]`` whose ``__pydantic_generic_metadata__`` names the
    origin and the arguments.
    """
    for klass in cls.__mro__:
        metadata = getattr(klass, "__pydantic_generic_metadata__", None)
        if metadata is not None and metadata["origin"] is origin:
            (argument,) = metadata["args"]
            return argument
        for base in getattr(klass, "__orig_bases__", ()):
            if typing.get_origin(base) is origin:
                (argument,) = typing.get_args(base)
                return argument
    msg = f"{cls.__name__} does not subclass {origin.__name__}[...]"
    raise AssertionError(msg)


def _repository_ports() -> list[tuple[str, type]]:
    ports: list[tuple[str, type]] = []
    for boundary in sorted(boundaries()):
        if not any(
            boundary.startswith(f"{context_module(name)}.application.port.outbound.") for name in context_names()
        ):
            continue
        package = importlib.import_module(boundary)
        for name in package.__all__:
            value = getattr(package, name)
            if isinstance(value, type) and issubclass(value, Repository) and value is not Repository:
                ports.append((boundary, value))
    return ports


@pytest.mark.parametrize(
    ("boundary", "repo"),
    _repository_ports(),
    ids=lambda value: value if isinstance(value, str) else value.__name__,
)
def test_repository_port_exports_its_aggregate_and_id(boundary: str, repo: type):
    """Adapters see only ports, so a repo port re-exports its aggregate and the id type."""
    aggregate = _generic_argument(repo, Repository)
    entity_id = _generic_argument(aggregate, AggregateRoot)
    package = importlib.import_module(boundary)
    for exported in (aggregate, entity_id):
        assert getattr(package, exported.__name__, None) is exported, (
            f"{boundary} must re-export {exported.__name__} (used by {repo.__name__})"
        )
        assert exported.__name__ in package.__all__, exported.__name__


class _GadgetId(EntityId):
    """Identify a gadget."""


class _Gadget(AggregateRoot[_GadgetId]):
    """An aggregate."""


class _GadgetsRepo(Repository[_Gadget]):
    """A repository port."""


def test_generic_argument_reads_the_id_of_an_aggregate_root():
    """The id type is read from the Pydantic generic base."""
    assert _generic_argument(_Gadget, AggregateRoot) is _GadgetId


def test_generic_argument_reads_the_aggregate_of_a_repository():
    """The aggregate is read from the plain generic base."""
    assert _generic_argument(_GadgetsRepo, Repository) is _Gadget


def test_generic_argument_reports_a_missing_generic_base():
    """A class without the generic base is reported, naming the base."""
    with pytest.raises(AssertionError, match="does not subclass AggregateRoot"):
        _generic_argument(_GadgetId, AggregateRoot)


def aggregates_without_one_repository_port(wanted: set[str], counts: dict[str, int]) -> list[str]:
    """Return the aggregates in ``wanted`` that do not have exactly one repository port in ``counts``."""
    return sorted(name for name in wanted if counts.get(name, 0) != 1)


def repository_port_counts(module: str, context_root: Path) -> dict[str, int]:
    """Count the repository ports each ``application/port/outbound/<aggregate>`` package of a context exports."""
    outbound = context_root / "application" / "port" / "outbound"
    counts: dict[str, int] = {}
    for package_dir in sorted(outbound.iterdir()):
        if not (package_dir / "__init__.py").is_file():
            continue
        package = importlib.import_module(f"{module}.application.port.outbound.{package_dir.name}")
        counts[package_dir.name] = sum(
            1
            for name in package.__all__
            if isinstance(value := getattr(package, name), type)
            and issubclass(value, Repository)
            and value is not Repository
        )
    return counts


@pytest.mark.parametrize("context", context_names())
def test_each_aggregate_has_one_repository_port_per_context(context: str):
    """Every aggregate of a context has exactly one repository port in its own outbound port package."""
    counts = repository_port_counts(context_module(context), context_dir(context))
    assert aggregates_without_one_repository_port(aggregates(context), counts) == []


def test_missing_or_duplicate_repository_port_is_reported():
    """An aggregate with no repository port, or with two, is reported."""
    assert aggregates_without_one_repository_port({"a", "b", "c"}, {"a": 1, "c": 2}) == ["b", "c"]


_AGGREGATE_MODEL = '''"""An aggregate."""

from __future__ import annotations

from base import AggregateRoot, EntityId


class {name}Id(EntityId):
    """Identify a {name}."""


class {name}(AggregateRoot[{name}Id]):
    """A {name}."""
'''
_REPO_PORTS = '''"""Repository ports."""

from __future__ import annotations

from base import Entity, Repository

{classes}

__all__ = [{exports}]
'''


def _repo_ports_source(name: str, repos: int) -> str:
    classes = "\n\n".join(f"class {name}Repo{i}(Repository[Entity]):\n    '''A repo.'''\n" for i in range(repos))
    exports = ", ".join(f'"{name}Repo{i}"' for i in range(repos))
    return _REPO_PORTS.format(classes=classes, exports=exports)


def test_context_with_missing_and_duplicate_repository_ports_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """In a fixture context, an aggregate without a repo port and one with two are both reported."""
    layout = {"sprocket": 1, "gadget": 0, "widget": 2}
    files: dict[str, str] = {}
    for aggregate, repos in layout.items():
        files[f"application/domain/model/{aggregate}/__init__.py"] = _AGGREGATE_MODEL.format(
            name=aggregate.capitalize()
        )
        files[f"application/port/outbound/{aggregate}/__init__.py"] = (
            _repo_ports_source(aggregate.capitalize(), repos)
            if repos
            else '"""No repo."""\n\n__all__: list[str] = []\n'
        )
    package = build_fixture_context(tmp_path, files)
    monkeypatch.syspath_prepend(str(tmp_path))
    counts = repository_port_counts(package, tmp_path / package)
    assert counts == layout
    wanted = derive_aggregates(f"{package}.application.domain.model")
    assert aggregates_without_one_repository_port(wanted, counts) == ["gadget", "widget"]


BOUNDARY_FREE_MODULES = {
    "bootstrap.api",
    "bootstrap.worker",
    "bootstrap.event_consumer",
    "bootstrap.migrate",
    "bootstrap.export_openapi",
}


def test_every_project_module_belongs_to_a_boundary():
    """A new module cannot escape the boundary test by living outside every boundary."""
    known = boundaries()
    outside = [
        _module_name(path)
        for path in _source_files()
        if _is_project(_module_name(path))
        and path.name != "__init__.py"
        and innermost_boundary(_module_name(path), known) is None
    ]
    assert sorted(outside) == sorted(BOUNDARY_FREE_MODULES), "Modules outside every boundary:\n" + "\n".join(
        sorted(outside)
    )
