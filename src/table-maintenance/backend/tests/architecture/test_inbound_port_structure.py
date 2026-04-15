"""Guard tests for inbound port directory structure and naming conventions.

Each use case under port/inbound/ must be a directory containing exactly:
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


def _use_case_dirs() -> list[Path]:
    """Return all use case directories under port/inbound/."""
    return [
        d for d in INBOUND_PORT_DIR.iterdir() if d.is_dir() and d.name != "__pycache__"
    ]


def _pascal_to_words(name: str) -> str:
    """Convert directory name like 'get_job' to PascalCase prefix like 'GetJob'."""
    return "".join(word.capitalize() for word in name.split("_"))


# --- Rule 1: No loose .py files (only __init__.py and directories) ---


def test_no_loose_py_files_in_inbound_port():
    loose_files = [
        f.name
        for f in INBOUND_PORT_DIR.iterdir()
        if f.is_file() and f.suffix == ".py" and f.name != "__init__.py"
    ]
    assert loose_files == [], (
        f"Found loose .py files in port/inbound/ — each use case must be a directory: {loose_files}"
    )


# --- Rule 2: Each use case directory has exactly the required files ---


@pytest.mark.parametrize("use_case_dir", _use_case_dirs(), ids=lambda d: d.name)
def test_use_case_dir_has_required_files(use_case_dir: Path):
    actual_files = {
        f.name for f in use_case_dir.iterdir() if f.is_file() and f.suffix == ".py"
    }
    assert REQUIRED_FILES.issubset(actual_files), (
        f"{use_case_dir.name}/ is missing: {REQUIRED_FILES - actual_files}"
    )


@pytest.mark.parametrize("use_case_dir", _use_case_dirs(), ids=lambda d: d.name)
def test_use_case_dir_has_no_extra_files(use_case_dir: Path):
    actual_files = {
        f.name for f in use_case_dir.iterdir() if f.is_file() and f.suffix == ".py"
    }
    extra = actual_files - REQUIRED_FILES
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


@pytest.mark.parametrize("use_case_dir", _use_case_dirs(), ids=lambda d: d.name)
def test_input_class_naming(use_case_dir: Path):
    prefix = _pascal_to_words(use_case_dir.name)
    expected = f"{prefix}Input"
    module = f"application.port.inbound.{use_case_dir.name}.input"
    classes = _exported_classes(module)
    assert expected in classes, (
        f"{use_case_dir.name}/input.py must export '{expected}', found: {classes}"
    )


@pytest.mark.parametrize("use_case_dir", _use_case_dirs(), ids=lambda d: d.name)
def test_output_class_naming(use_case_dir: Path):
    prefix = _pascal_to_words(use_case_dir.name)
    expected = f"{prefix}Output"
    module = f"application.port.inbound.{use_case_dir.name}.output"
    classes = _exported_classes(module)
    assert expected in classes, (
        f"{use_case_dir.name}/output.py must export '{expected}', found: {classes}"
    )


@pytest.mark.parametrize("use_case_dir", _use_case_dirs(), ids=lambda d: d.name)
def test_use_case_class_naming(use_case_dir: Path):
    prefix = _pascal_to_words(use_case_dir.name)
    expected = f"{prefix}UseCase"
    module = f"application.port.inbound.{use_case_dir.name}.use_case"
    classes = _exported_classes(module)
    assert expected in classes, (
        f"{use_case_dir.name}/use_case.py must export '{expected}', found: {classes}"
    )


# --- Rule 4: __init__.py re-exports all three symbols ---


@pytest.mark.parametrize("use_case_dir", _use_case_dirs(), ids=lambda d: d.name)
def test_init_reexports_all_symbols(use_case_dir: Path):
    prefix = _pascal_to_words(use_case_dir.name)
    expected_symbols = {f"{prefix}Input", f"{prefix}Output", f"{prefix}UseCase"}
    module = f"application.port.inbound.{use_case_dir.name}"
    mod = importlib.import_module(module)
    exported = set(getattr(mod, "__all__", []))
    missing = expected_symbols - exported
    assert missing == set(), (
        f"{use_case_dir.name}/__init__.py must re-export {missing} in __all__"
    )
