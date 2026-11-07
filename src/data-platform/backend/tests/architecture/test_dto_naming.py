"""Guard DTO naming conventions for the web adapter layer.

Inbound and outbound port DTO naming is already enforced by
test_inbound_port_structure.py and test_outbound_port_structure.py.

This test enforces the web adapter rule:
  - Every class defined in adapter/inbound/web/**/dto.py must end with
    'ApiRequest' or 'ApiResponse'.

No prefix rule is enforced for web DTOs — verb prefix is convention,
not requirement, since some DTOs represent shared resources or nested
sub-components.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.architecture.contexts import CONTEXT_ROOT, context_dir, context_names


_ALLOWED_SUFFIXES = ("ApiRequest", "ApiResponse")


def _defined_classes(file_path: Path) -> list[str]:
    """Return class names defined in a Python file."""
    source = file_path.read_text()
    tree = ast.parse(source)
    return [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


def _dto_files() -> list[Path]:
    """Find all dto.py files under the web adapter directories of every context."""
    return sorted(
        path for name in context_names() for path in (context_dir(name) / "adapter" / "inbound" / "web").rglob("dto.py")
    )


def _dto_id(file_path: Path) -> str:
    context = file_path.relative_to(CONTEXT_ROOT).parts[0]
    return f"{context}/web/{file_path.parent.name}/dto.py"


@pytest.mark.parametrize("file_path", _dto_files(), ids=_dto_id)
def test_web_dto_suffix(file_path: Path) -> None:
    """Verify every class in dto.py ends with ApiRequest or ApiResponse."""
    misnamed = [cls for cls in _defined_classes(file_path) if not any(cls.endswith(s) for s in _ALLOWED_SUFFIXES)]
    assert misnamed == [], f"{file_path.parent.name}/dto.py has classes not ending with {_ALLOWED_SUFFIXES}: {misnamed}"
