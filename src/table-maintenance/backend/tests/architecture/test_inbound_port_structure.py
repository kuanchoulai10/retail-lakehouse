"""Guard tests for inbound port directory structure and naming conventions.

Use cases are grouped under port/inbound/{aggregate}/ (e.g. job/, job_run/).
Each use case directory must contain exactly:
  __init__.py, input.py, output.py, use_case.py

Naming convention:
  {Name}Input  in input.py
  {Name}Output in output.py
  {Name}UseCase in use_case.py

__init__.py must re-export all three symbols.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

INBOUND_PORT_DIR = (
    Path(__file__).resolve().parents[2] / "application" / "port" / "inbound"
)
REQUIRED_FILES = {"__init__.py", "input.py", "output.py", "use_case.py"}
REQUIRED_FILES_NO_INPUT = {"__init__.py", "output.py", "use_case.py"}
ALLOWED_FILES = REQUIRED_FILES  # input.py is optional for no-input use cases

AGGREGATE_GROUPS = ["catalog", "job", "job_run", "outbox", "scheduling"]
AGGREGATE_GROUPS_NO_INPUT = {"outbox", "scheduling"}


def _group_dirs() -> list[Path]:
    """Return aggregate grouping directories under port/inbound/."""
    return [INBOUND_PORT_DIR / name for name in AGGREGATE_GROUPS]


def _use_case_dirs() -> list[tuple[str, Path]]:
    """Return (group, path) for all use case directories under port/inbound/{group}/."""
    result: list[tuple[str, Path]] = []
    for group_dir in _group_dirs():
        for d in sorted(group_dir.iterdir()):
            if d.is_dir() and d.name != "__pycache__":
                result.append((group_dir.name, d))
    return result


def _pascal_to_words(name: str) -> str:
    """Convert directory name like 'get_job' to PascalCase prefix like 'GetJob'."""
    return "".join(word.capitalize() for word in name.split("_"))


def _use_case_id(param: tuple[str, Path]) -> str:
    """Format a use case entry as a readable pytest ID."""
    group, d = param
    return f"{group}/{d.name}"


# --- Rule 1: No loose .py files (only __init__.py and group directories) ---


def test_no_loose_py_files_in_inbound_port():
    """Verify that port/inbound/ contains no loose .py files besides __init__.py."""
    loose_files = [
        f.name
        for f in INBOUND_PORT_DIR.iterdir()
        if f.is_file() and f.suffix == ".py" and f.name != "__init__.py"
    ]
    assert loose_files == [], (
        f"Found loose .py files in port/inbound/ — each use case must be a directory: {loose_files}"
    )


def test_only_aggregate_groups_in_inbound_port():
    """Verify that port/inbound/ contains only the expected aggregate group directories."""
    dirs = [
        d.name
        for d in INBOUND_PORT_DIR.iterdir()
        if d.is_dir() and d.name != "__pycache__"
    ]
    assert sorted(dirs) == sorted(AGGREGATE_GROUPS), (
        f"port/inbound/ must only contain aggregate groups {AGGREGATE_GROUPS}, found: {dirs}"
    )


# --- Rule 2: Each use case directory has exactly the required files ---


@pytest.mark.parametrize("use_case_entry", _use_case_dirs(), ids=_use_case_id)
def test_use_case_dir_has_required_files(use_case_entry: tuple[str, Path]):
    """Verify that each use case directory contains all required files."""
    group, use_case_dir = use_case_entry
    actual_files = {
        f.name for f in use_case_dir.iterdir() if f.is_file() and f.suffix == ".py"
    }
    required = (
        REQUIRED_FILES_NO_INPUT
        if group in AGGREGATE_GROUPS_NO_INPUT
        else REQUIRED_FILES
    )
    assert required.issubset(actual_files), (
        f"{use_case_dir.name}/ is missing: {required - actual_files}"
    )


@pytest.mark.parametrize("use_case_entry", _use_case_dirs(), ids=_use_case_id)
def test_use_case_dir_has_no_extra_files(use_case_entry: tuple[str, Path]):
    """Verify that each use case directory contains no unexpected files."""
    _group, use_case_dir = use_case_entry
    actual_files = {
        f.name for f in use_case_dir.iterdir() if f.is_file() and f.suffix == ".py"
    }
    extra = actual_files - ALLOWED_FILES
    assert extra == set(), f"{use_case_dir.name}/ has unexpected files: {extra}"


# --- Rule 3: Naming conventions ---


def _exported_classes(module_path: str) -> list[str]:
    """Return class names defined in a module."""
    mod = importlib.import_module(module_path)
    return [
        name
        for name in dir(mod)
        if isinstance(getattr(mod, name), type) and not name.startswith("_")
    ]


@pytest.mark.parametrize("use_case_entry", _use_case_dirs(), ids=_use_case_id)
def test_input_class_naming(use_case_entry: tuple[str, Path]):
    """Verify that input.py exports a class named {PascalCase}Input."""
    group, use_case_dir = use_case_entry
    if group in AGGREGATE_GROUPS_NO_INPUT:
        pytest.skip("No-input use case")
    prefix = _pascal_to_words(use_case_dir.name)
    expected = f"{prefix}Input"
    module = f"application.port.inbound.{group}.{use_case_dir.name}.input"
    classes = _exported_classes(module)
    assert expected in classes, (
        f"{use_case_dir.name}/input.py must export '{expected}', found: {classes}"
    )


@pytest.mark.parametrize("use_case_entry", _use_case_dirs(), ids=_use_case_id)
def test_output_class_naming(use_case_entry: tuple[str, Path]):
    """Verify that output.py exports a class named {PascalCase}Output or {PascalCase}Result."""
    group, use_case_dir = use_case_entry
    prefix = _pascal_to_words(use_case_dir.name)
    expected_output = f"{prefix}Output"
    expected_result = f"{prefix}Result"
    module = f"application.port.inbound.{group}.{use_case_dir.name}.output"
    classes = _exported_classes(module)
    assert expected_output in classes or expected_result in classes, (
        f"{use_case_dir.name}/output.py must export '{expected_output}' or '{expected_result}', found: {classes}"
    )


@pytest.mark.parametrize("use_case_entry", _use_case_dirs(), ids=_use_case_id)
def test_use_case_class_naming(use_case_entry: tuple[str, Path]):
    """Verify that use_case.py exports a class named {PascalCase}UseCase."""
    group, use_case_dir = use_case_entry
    prefix = _pascal_to_words(use_case_dir.name)
    expected = f"{prefix}UseCase"
    module = f"application.port.inbound.{group}.{use_case_dir.name}.use_case"
    classes = _exported_classes(module)
    assert expected in classes, (
        f"{use_case_dir.name}/use_case.py must export '{expected}', found: {classes}"
    )


# --- Rule 4: __init__.py re-exports all three symbols ---


@pytest.mark.parametrize("use_case_entry", _use_case_dirs(), ids=_use_case_id)
def test_init_reexports_all_symbols(use_case_entry: tuple[str, Path]):
    """Verify that __init__.py re-exports Input, Output/Result, and UseCase in __all__."""
    group, use_case_dir = use_case_entry
    prefix = _pascal_to_words(use_case_dir.name)
    module = f"application.port.inbound.{group}.{use_case_dir.name}"
    mod = importlib.import_module(module)
    exported = set(getattr(mod, "__all__", []))

    # UseCase is always required
    assert f"{prefix}UseCase" in exported, (
        f"{use_case_dir.name}/__init__.py must re-export '{prefix}UseCase' in __all__"
    )
    # Output or Result is required
    assert f"{prefix}Output" in exported or f"{prefix}Result" in exported, (
        f"{use_case_dir.name}/__init__.py must re-export '{prefix}Output' or '{prefix}Result' in __all__"
    )
    # Input is required only for groups with input
    if group not in AGGREGATE_GROUPS_NO_INPUT:
        assert f"{prefix}Input" in exported, (
            f"{use_case_dir.name}/__init__.py must re-export '{prefix}Input' in __all__"
        )
