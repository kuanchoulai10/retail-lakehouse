from __future__ import annotations

import importlib

import pytest

import entrypoint
from bootstrap.configs import Component


@pytest.mark.parametrize(
    "module",
    [
        "bootstrap.api",
        "bootstrap.worker",
        "bootstrap.event_consumer",
        "bootstrap.migrate",
    ],
)
def test_component_modules_import_without_side_effects(module: str):
    loaded = importlib.import_module(module)

    assert callable(loaded.main)


@pytest.mark.parametrize(
    ("component", "module"),
    [
        (Component.API, "bootstrap.api"),
        (Component.WORKER, "bootstrap.worker"),
        (Component.EVENT_CONSUMER, "bootstrap.event_consumer"),
        (Component.MIGRATE, "bootstrap.migrate"),
    ],
)
def test_entrypoint_dispatches_to_the_component(monkeypatch: pytest.MonkeyPatch, component: Component, module: str):
    called: list[str] = []
    monkeypatch.setenv("GLAC_COMPONENT", component.value)
    monkeypatch.setattr(importlib.import_module(module), "main", lambda: called.append(module))
    entrypoint.get_settings.cache_clear()
    try:
        entrypoint.main()
    finally:
        entrypoint.get_settings.cache_clear()

    assert called == [module]
