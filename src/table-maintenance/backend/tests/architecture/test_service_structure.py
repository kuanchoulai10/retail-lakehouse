"""Guard tests for application service naming conventions and compliance.

Rules enforced:
  Service files (*not* ending in _handler.py):
    1. Must define a class ending in "Service"
    2. Service names should start with a known verb (best-effort, warns on unknown)
    3. Every *Service class must be a subclass of UseCase

  Handler files (*_handler.py):
    4. Must define a class ending in "Handler"
    5. Every *Handler class must be a subclass of EventHandler
"""

from __future__ import annotations

import importlib
import inspect
import re
import warnings
from pathlib import Path

import pytest

from base.event_handler import EventHandler
from base.use_case import UseCase

SERVICE_DIR = Path(__file__).resolve().parents[2] / "application" / "service"

# Files that are utilities, not services — excluded from service rules
UTILITY_FILES = {"event_serializer.py"}

# Known verbs for service naming. This is a pre-defined allowlist, not an
# exhaustive restriction. If a new verb is legitimate, add it here.
KNOWN_VERBS = {
    # CRUD
    "Create",
    "Get",
    "List",
    "Update",
    "Delete",
    # Lifecycle
    "Start",
    "Stop",
    "Cancel",
    "Retry",
    "Resume",
    "Pause",
    "Archive",
    # Process
    "Schedule",
    "Publish",
    "Execute",
    "Run",
    "Process",
    "Submit",
    "Trigger",
    # Data
    "Import",
    "Export",
    "Sync",
    "Validate",
    "Search",
}


def _all_modules() -> list[tuple[str, Path]]:
    """Return (dotted module path, file path) for all non-utility .py files."""
    result: list[tuple[str, Path]] = []
    for py_file in sorted(SERVICE_DIR.rglob("*.py")):
        if py_file.name == "__init__.py":
            continue
        if py_file.name in UTILITY_FILES:
            continue
        relative = py_file.relative_to(SERVICE_DIR.parents[1])
        module_path = str(relative.with_suffix("")).replace("/", ".")
        result.append((module_path, py_file))
    return result


def _service_modules() -> list[tuple[str, Path]]:
    """Return modules that are services (not handlers)."""
    return [(m, p) for m, p in _all_modules() if not p.name.endswith("_handler.py")]


def _handler_modules() -> list[tuple[str, Path]]:
    """Return modules that are event handlers."""
    return [(m, p) for m, p in _all_modules() if p.name.endswith("_handler.py")]


def _module_id(param: tuple[str, Path]) -> str:
    """Format a module entry as a readable pytest ID."""
    _module, path = param
    return str(path.relative_to(SERVICE_DIR))


def _find_defined_classes(module_path: str) -> list[tuple[str, type]]:
    """Import a module and return classes defined in it (not imported)."""
    mod = importlib.import_module(module_path)
    return [
        (name, cls)
        for name, cls in inspect.getmembers(mod, inspect.isclass)
        if cls.__module__ == module_path and not name.startswith("_")
    ]


def _extract_first_word(class_name: str) -> str | None:
    """Extract the first PascalCase word from a class name.

    Example: 'CreateJobService' → 'Create', 'ListJobsService' → 'List'
    """
    match = re.match(r"([A-Z][a-z]+)", class_name)
    return match.group(1) if match else None


# --- Rule 1: Service class naming ---


@pytest.mark.parametrize("service_entry", _service_modules(), ids=_module_id)
def test_service_class_ends_with_service(service_entry: tuple[str, Path]):
    """Verify that each service module defines a class ending in 'Service'."""
    module_path, py_file = service_entry
    classes = _find_defined_classes(module_path)
    service_classes = [name for name, _cls in classes if name.endswith("Service")]
    assert service_classes, (
        f"{py_file.name} must define a class ending in 'Service', "
        f"found: {[name for name, _ in classes]}"
    )


# --- Rule 2: Verb-first naming (best effort) ---


@pytest.mark.parametrize("service_entry", _service_modules(), ids=_module_id)
def test_service_name_starts_with_known_verb(service_entry: tuple[str, Path]):
    """Warn if service name doesn't start with a known verb."""
    module_path, _py_file = service_entry
    classes = _find_defined_classes(module_path)
    for name, _cls in classes:
        if not name.endswith("Service"):
            continue
        first_word = _extract_first_word(name)
        if first_word and first_word not in KNOWN_VERBS:
            warnings.warn(
                f"'{name}' starts with '{first_word}' which is not in the "
                f"known verb list: {sorted(KNOWN_VERBS)}. "
                f"This is a pre-defined allowlist, not an exhaustive restriction. "
                f"If '{first_word}' is a legitimate verb, add it to KNOWN_VERBS "
                f"in {Path(__file__).name}.",
                stacklevel=1,
            )


# --- Rule 3: Service must implement UseCase ---


@pytest.mark.parametrize("service_entry", _service_modules(), ids=_module_id)
def test_service_implements_use_case(service_entry: tuple[str, Path]):
    """Verify that every *Service class is a subclass of UseCase."""
    module_path, py_file = service_entry
    classes = _find_defined_classes(module_path)
    for name, cls in classes:
        if not name.endswith("Service"):
            continue
        assert issubclass(cls, UseCase), (
            f"{name} in {py_file.name} must implement a UseCase interface, "
            f"but its bases are: {[b.__name__ for b in cls.__mro__]}"
        )


# --- Rule 4: Handler class naming ---


@pytest.mark.parametrize("handler_entry", _handler_modules(), ids=_module_id)
def test_handler_class_ends_with_handler(handler_entry: tuple[str, Path]):
    """Verify that each handler module defines a class ending in 'Handler'."""
    module_path, py_file = handler_entry
    classes = _find_defined_classes(module_path)
    handler_classes = [name for name, _cls in classes if name.endswith("Handler")]
    assert handler_classes, (
        f"{py_file.name} must define a class ending in 'Handler', "
        f"found: {[name for name, _ in classes]}"
    )


# --- Rule 5: Handler must implement EventHandler ---


@pytest.mark.parametrize("handler_entry", _handler_modules(), ids=_module_id)
def test_handler_implements_event_handler(handler_entry: tuple[str, Path]):
    """Verify that every *Handler class is a subclass of EventHandler."""
    module_path, py_file = handler_entry
    classes = _find_defined_classes(module_path)
    for name, cls in classes:
        if not name.endswith("Handler"):
            continue
        assert issubclass(cls, EventHandler), (
            f"{name} in {py_file.name} must implement EventHandler, "
            f"but its bases are: {[b.__name__ for b in cls.__mro__]}"
        )
