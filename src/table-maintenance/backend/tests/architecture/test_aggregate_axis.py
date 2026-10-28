"""Guard test: every layer directory is split by the same aggregate axis."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.architecture.aggregates import AGGREGATES

BACKEND = Path(__file__).resolve().parents[2]

LAYER_DIRS = [
    "application/domain/model",
    "application/domain/service",
    "application/port/inbound",
    "application/service",
    "adapter/inbound/web",
    "application/port/outbound",
    "adapter/outbound",
    "adapter/hybrid/temporal/outbound",
]
ROOT_MODULE_EXEMPT = {"adapter/inbound/web"}


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
    ports = subdirs("application/port/inbound")
    assert "shared" not in ports
    assert ports == subdirs("application/service") - {"shared"}


@pytest.mark.parametrize(
    "layer", [layer for layer in LAYER_DIRS if layer not in ROOT_MODULE_EXEMPT]
)
def test_no_modules_at_layer_root(layer: str):
    modules = {p.name for p in (BACKEND / layer).glob("*.py")}
    assert modules == {"__init__.py"}, f"{layer} root holds modules: {sorted(modules)}"
