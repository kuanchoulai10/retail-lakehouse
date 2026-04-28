"""Guard tests for outbound port directory structure and naming conventions.

Outbound ports are grouped under port/outbound/{aggregate}/.

Three port types exist:
  - Repository: flat file, class extends Repository
  - Store: flat file, class extends Store
  - Gateway: subdirectory with gateway.py, optional input.py/output.py

Gateway subdirectory must contain:
  Required: __init__.py, gateway.py
  Optional: input.py, output.py

Naming convention for Gateway subdirectory {verb}_{noun}/:
  {Verb}{Noun}Gateway        in gateway.py
  {Verb}{Noun}GatewayInput   in input.py   (if present, primitive-only imports)
  {Verb}{Noun}GatewayOutput  in output.py  (if present, primitive-only imports)

__init__.py must re-export all symbols via __all__.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

from base.gateway import Gateway

OUTBOUND_PORT_DIR = (
    Path(__file__).resolve().parents[2] / "application" / "port" / "outbound"
)

AGGREGATE_GROUPS = ["catalog", "event_outbox", "job", "job_run"]

GATEWAY_REQUIRED_FILES = {"__init__.py", "gateway.py"}
GATEWAY_ALLOWED_FILES = {"__init__.py", "gateway.py", "input.py", "output.py"}

# Imports allowed in input.py / output.py (primitive-only constraint).
# These files must NOT import from application.domain or base (except base.value_object).
ALLOWED_INPUT_OUTPUT_IMPORT_PREFIXES = (
    "from __future__",
    "from dataclasses",
    "from typing",
    "from base.value_object",
    "import dataclasses",
    "import typing",
)


def _gateway_dirs() -> list[tuple[str, Path]]:
    """Return (aggregate, path) for all gateway subdirectories."""
    result: list[tuple[str, Path]] = []
    for group_name in AGGREGATE_GROUPS:
        group_dir = OUTBOUND_PORT_DIR / group_name
        if not group_dir.is_dir():
            continue
        for d in sorted(group_dir.iterdir()):
            if d.is_dir() and d.name != "__pycache__":
                result.append((group_name, d))
    return result


def _gateway_id(param: tuple[str, Path]) -> str:
    """Format a gateway entry as a readable pytest ID."""
    group, d = param
    return f"{group}/{d.name}"


def _pascal_case(name: str) -> str:
    """Convert 'submit_job_run' to 'SubmitJobRun'."""
    return "".join(word.capitalize() for word in name.split("_"))


def _exported_classes(module_path: str) -> list[str]:
    """Return class names defined in a module."""
    mod = importlib.import_module(module_path)
    return [
        name
        for name in dir(mod)
        if isinstance(getattr(mod, name), type) and not name.startswith("_")
    ]


def _parse_imports(file_path: Path) -> list[str]:
    """Return all import statements from a file as source lines."""
    source = file_path.read_text()
    tree = ast.parse(source)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(f"from {node.module}")
    return imports


# --- Rule 1: Only aggregate group directories exist ---


def test_only_aggregate_groups_in_outbound_port():
    """Verify that port/outbound/ contains only the expected aggregate group directories."""
    dirs = [
        d.name
        for d in OUTBOUND_PORT_DIR.iterdir()
        if d.is_dir() and d.name != "__pycache__"
    ]
    assert sorted(dirs) == sorted(AGGREGATE_GROUPS), (
        f"port/outbound/ must only contain aggregate groups {AGGREGATE_GROUPS}, found: {dirs}"
    )


# --- Rule 2: Gateway directory has required files ---


@pytest.mark.parametrize("gw_entry", _gateway_dirs(), ids=_gateway_id)
def test_gateway_dir_has_required_files(gw_entry: tuple[str, Path]):
    """Verify that each gateway directory contains __init__.py and gateway.py."""
    _group, gw_dir = gw_entry
    actual_files = {
        f.name for f in gw_dir.iterdir() if f.is_file() and f.suffix == ".py"
    }
    missing = GATEWAY_REQUIRED_FILES - actual_files
    assert missing == set(), f"{gw_dir.name}/ is missing: {missing}"


@pytest.mark.parametrize("gw_entry", _gateway_dirs(), ids=_gateway_id)
def test_gateway_dir_has_no_extra_files(gw_entry: tuple[str, Path]):
    """Verify that each gateway directory contains no unexpected files."""
    _group, gw_dir = gw_entry
    actual_files = {
        f.name for f in gw_dir.iterdir() if f.is_file() and f.suffix == ".py"
    }
    extra = actual_files - GATEWAY_ALLOWED_FILES
    assert extra == set(), f"{gw_dir.name}/ has unexpected files: {extra}"


# --- Rule 3: gateway.py class naming and base class ---


@pytest.mark.parametrize("gw_entry", _gateway_dirs(), ids=_gateway_id)
def test_gateway_class_naming(gw_entry: tuple[str, Path]):
    """Verify that gateway.py exports {Verb}{Noun}Gateway extending Gateway."""
    group, gw_dir = gw_entry
    prefix = _pascal_case(gw_dir.name)
    expected = f"{prefix}Gateway"
    module = f"application.port.outbound.{group}.{gw_dir.name}.gateway"
    classes = _exported_classes(module)
    assert expected in classes, (
        f"{gw_dir.name}/gateway.py must export '{expected}', found: {classes}"
    )


@pytest.mark.parametrize("gw_entry", _gateway_dirs(), ids=_gateway_id)
def test_gateway_extends_base(gw_entry: tuple[str, Path]):
    """Verify that the Gateway class extends base.gateway.Gateway."""
    group, gw_dir = gw_entry
    prefix = _pascal_case(gw_dir.name)
    expected = f"{prefix}Gateway"
    module = f"application.port.outbound.{group}.{gw_dir.name}.gateway"
    mod = importlib.import_module(module)
    cls = getattr(mod, expected)
    assert issubclass(cls, Gateway), (
        f"{expected} must extend Gateway, bases: {[b.__name__ for b in cls.__mro__]}"
    )


# --- Rule 4: input.py class naming (if exists) ---


@pytest.mark.parametrize("gw_entry", _gateway_dirs(), ids=_gateway_id)
def test_input_class_naming(gw_entry: tuple[str, Path]):
    """Verify that input.py exports {Verb}{Noun}GatewayInput (if present)."""
    group, gw_dir = gw_entry
    input_file = gw_dir / "input.py"
    if not input_file.exists():
        pytest.skip("No input.py")
    prefix = _pascal_case(gw_dir.name)
    expected = f"{prefix}GatewayInput"
    module = f"application.port.outbound.{group}.{gw_dir.name}.input"
    classes = _exported_classes(module)
    assert expected in classes, (
        f"{gw_dir.name}/input.py must export '{expected}', found: {classes}"
    )


# --- Rule 5: output.py class naming (if exists) ---


@pytest.mark.parametrize("gw_entry", _gateway_dirs(), ids=_gateway_id)
def test_output_class_naming(gw_entry: tuple[str, Path]):
    """Verify that output.py exports {Verb}{Noun}GatewayOutput (if present)."""
    group, gw_dir = gw_entry
    output_file = gw_dir / "output.py"
    if not output_file.exists():
        pytest.skip("No output.py")
    prefix = _pascal_case(gw_dir.name)
    expected = f"{prefix}GatewayOutput"
    module = f"application.port.outbound.{group}.{gw_dir.name}.output"
    classes = _exported_classes(module)
    assert expected in classes, (
        f"{gw_dir.name}/output.py must export '{expected}', found: {classes}"
    )


# --- Rule 6: input.py / output.py primitive-only imports ---


@pytest.mark.parametrize("gw_entry", _gateway_dirs(), ids=_gateway_id)
def test_input_primitive_only(gw_entry: tuple[str, Path]):
    """Verify that input.py does not import domain or base types (except ValueObject)."""
    _group, gw_dir = gw_entry
    input_file = gw_dir / "input.py"
    if not input_file.exists():
        pytest.skip("No input.py")
    imports = _parse_imports(input_file)
    violations = [
        imp
        for imp in imports
        if not any(
            imp.startswith(prefix) for prefix in ALLOWED_INPUT_OUTPUT_IMPORT_PREFIXES
        )
    ]
    assert violations == [], (
        f"{gw_dir.name}/input.py has non-primitive imports: {violations}"
    )


@pytest.mark.parametrize("gw_entry", _gateway_dirs(), ids=_gateway_id)
def test_output_primitive_only(gw_entry: tuple[str, Path]):
    """Verify that output.py does not import domain or base types (except ValueObject)."""
    _group, gw_dir = gw_entry
    output_file = gw_dir / "output.py"
    if not output_file.exists():
        pytest.skip("No output.py")
    imports = _parse_imports(output_file)
    violations = [
        imp
        for imp in imports
        if not any(
            imp.startswith(prefix) for prefix in ALLOWED_INPUT_OUTPUT_IMPORT_PREFIXES
        )
    ]
    assert violations == [], (
        f"{gw_dir.name}/output.py has non-primitive imports: {violations}"
    )


# --- Rule 7: __init__.py re-exports all symbols ---


@pytest.mark.parametrize("gw_entry", _gateway_dirs(), ids=_gateway_id)
def test_init_reexports_all_symbols(gw_entry: tuple[str, Path]):
    """Verify that __init__.py re-exports Gateway, Input, Output via __all__."""
    group, gw_dir = gw_entry
    prefix = _pascal_case(gw_dir.name)
    module = f"application.port.outbound.{group}.{gw_dir.name}"
    mod = importlib.import_module(module)
    exported = set(getattr(mod, "__all__", []))

    # Gateway is always required
    assert f"{prefix}Gateway" in exported, (
        f"{gw_dir.name}/__init__.py must re-export '{prefix}Gateway' in __all__"
    )
    # GatewayInput is required if input.py exists
    if (gw_dir / "input.py").exists():
        assert f"{prefix}GatewayInput" in exported, (
            f"{gw_dir.name}/__init__.py must re-export '{prefix}GatewayInput' in __all__"
        )
    # GatewayOutput is required if output.py exists
    if (gw_dir / "output.py").exists():
        assert f"{prefix}GatewayOutput" in exported, (
            f"{gw_dir.name}/__init__.py must re-export '{prefix}GatewayOutput' in __all__"
        )
