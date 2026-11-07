"""Guard test: every layer directory of a context is split by the same aggregate axis."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.architecture.aggregates import aggregates
from tests.architecture.contexts import context_dir, context_names

if TYPE_CHECKING:
    from pathlib import Path

FIXED_LAYER_DIRS = (
    "application/domain/model",
    "application/domain/service",
    "application/port/inbound",
    "application/service",
    "adapter/inbound/web",
    "application/port/outbound",
    "adapter/outbound",
)
ROOT_MODULES_ALLOWED = {
    "adapter/inbound/web": {
        "register_routes.py",
        "error_handlers.py",
    },
}


def subdirs(directory: Path) -> set[str]:
    """Return the names of the immediate subdirectories of a directory, ignoring caches."""
    return {
        child.name
        for child in directory.iterdir()
        if child.is_dir() and child.name != "__pycache__" and any(child.rglob("*.py"))
    }


def hybrid_outbound_dirs(context_root: Path) -> list[str]:
    """Return the hybrid outbound directories of a context, relative to the context root."""
    return sorted(
        str(path.relative_to(context_root))
        for path in (context_root / "adapter" / "hybrid").glob("*/outbound")
        if (path / "__init__.py").is_file()
    )


def layer_dirs(context_root: Path) -> list[str]:
    """Return every layer directory of a context that must be split by aggregate."""
    return [*FIXED_LAYER_DIRS, *hybrid_outbound_dirs(context_root)]


def axis_violations(context_root: Path, aggregates: set[str]) -> list[str]:
    """Return ``"<layer>: <dir>"`` for each layer directory that is not an aggregate."""
    allowed = aggregates | {"shared"}
    found: list[str] = []
    for layer in layer_dirs(context_root):
        directory = context_root / layer
        if not directory.is_dir():
            continue
        found += [f"{layer}: {name}" for name in sorted(subdirs(directory) - allowed)]
    return found


def _context_layers() -> list[tuple[str, str]]:
    return [(context, layer) for context in context_names() for layer in layer_dirs(context_dir(context))]


@pytest.mark.parametrize("context", context_names())
def test_layer_subdirs_are_aggregates(context: str):
    """Every subdirectory of an aggregate-split layer is a known aggregate or the shared package."""
    unexpected = axis_violations(context_dir(context), aggregates(context))
    assert not unexpected, f"{context} has non-aggregate directories: {unexpected}"


def test_directory_without_aggregate_root_fails_the_axis(tmp_path: Path):
    """A layer directory that matches no aggregate root is reported as a violation."""
    ghost = tmp_path / "application" / "service" / "ghost"
    ghost.mkdir(parents=True)
    (ghost / "__init__.py").write_text('"""Ghost."""\n')

    violations = axis_violations(tmp_path, {"widget"})

    assert violations == ["application/service: ghost"]


@pytest.mark.parametrize("context", context_names())
def test_inbound_ports_match_services(context: str):
    """The inbound port aggregates are exactly the service aggregates, apart from shared."""
    root = context_dir(context)
    ports = subdirs(root / "application" / "port" / "inbound")
    assert "shared" not in ports
    assert ports == subdirs(root / "application" / "service") - {"shared"}


@pytest.mark.parametrize("context", context_names())
def test_hybrid_outbound_dirs_are_found(context: str):
    """Every hybrid technology's outbound package is picked up as an aggregate-split layer."""
    root = context_dir(context)
    hybrid = root / "adapter" / "hybrid"
    expected = sorted(
        f"adapter/hybrid/{tech.name}/outbound"
        for tech in (hybrid.iterdir() if hybrid.is_dir() else [])
        if (tech / "outbound" / "__init__.py").is_file()
    )
    assert hybrid_outbound_dirs(root) == expected


def test_context_without_hybrid_has_no_hybrid_layers(tmp_path: Path):
    """A context with no hybrid directory has no hybrid layer and still passes the axis."""
    (tmp_path / "application" / "service" / "widget").mkdir(parents=True)
    (tmp_path / "application" / "service" / "widget" / "__init__.py").write_text("")
    assert hybrid_outbound_dirs(tmp_path) == []
    assert axis_violations(tmp_path, {"widget"}) == []


@pytest.mark.parametrize(("context", "layer"), _context_layers(), ids=lambda value: value)
def test_no_modules_at_layer_root(context: str, layer: str):
    """A layer root holds no loose modules beyond the allowed package files."""
    modules = {p.name for p in (context_dir(context) / layer).glob("*.py")}
    allowed = {"__init__.py"} | ROOT_MODULES_ALLOWED.get(layer, set())
    assert modules == allowed, f"{context}/{layer} root holds modules: {sorted(modules)}"
