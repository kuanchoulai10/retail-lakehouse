"""Guard test: every layer directory is split by the same aggregate axis."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.architecture.aggregates import AGGREGATES

BACKEND = Path(__file__).resolve().parents[2]

HYBRID_OUTBOUND_DIRS = sorted(
    str(path.relative_to(BACKEND))
    for path in (BACKEND / "context" / "table_maintenance" / "adapter" / "hybrid").glob(
        "*/outbound"
    )
    if (path / "__init__.py").is_file()
)
LAYER_DIRS = [
    "context/table_maintenance/application/domain/model",
    "context/table_maintenance/application/domain/service",
    "context/table_maintenance/application/port/inbound",
    "context/table_maintenance/application/service",
    "context/table_maintenance/adapter/inbound/web",
    "context/table_maintenance/application/port/outbound",
    "context/table_maintenance/adapter/outbound",
    *HYBRID_OUTBOUND_DIRS,
]
ROOT_MODULES_ALLOWED = {
    "context/table_maintenance/adapter/inbound/web": {
        "create_app.py",
        "error_handlers.py",
    },
}


def subdirs(layer: str) -> set[str]:
    return {
        child.name
        for child in (BACKEND / layer).iterdir()
        if child.is_dir() and child.name != "__pycache__" and any(child.rglob("*.py"))
    }


@pytest.mark.parametrize("layer", LAYER_DIRS)
def test_layer_subdirs_are_aggregates(layer: str):
    unexpected = subdirs(layer) - (AGGREGATES | {"shared"})
    assert not unexpected, (
        f"{layer} has non-aggregate directories: {sorted(unexpected)}"
    )


def test_inbound_ports_match_services():
    ports = subdirs("context/table_maintenance/application/port/inbound")
    assert "shared" not in ports
    assert ports == subdirs("context/table_maintenance/application/service") - {
        "shared"
    }


def test_hybrid_outbound_dirs_are_found():
    assert (
        "context/table_maintenance/adapter/hybrid/temporal/outbound"
        in HYBRID_OUTBOUND_DIRS
    )


@pytest.mark.parametrize("layer", LAYER_DIRS)
def test_no_modules_at_layer_root(layer: str):
    modules = {p.name for p in (BACKEND / layer).glob("*.py")}
    allowed = {"__init__.py"} | ROOT_MODULES_ALLOWED.get(layer, set())
    assert modules == allowed, f"{layer} root holds modules: {sorted(modules)}"
