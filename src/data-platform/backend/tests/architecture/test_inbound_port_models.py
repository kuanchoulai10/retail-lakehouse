"""Guard test: inbound port input and output are Pydantic models on ``UseCaseInput`` / ``UseCaseOutput``.

For every use-case directory ``context/<context>/application/port/inbound/<aggregate>/<use_case>/`` that is
not in ``PENDING_PORTS``:

- ``input.py`` (when present; a no-input use case has none) defines exactly one top-level class,
  ``{Name}UseCaseInput``, which extends ``UseCaseInput``; ``output.py`` likewise ``{Name}UseCaseOutput`` on
  ``UseCaseOutput``;
- nested classes are at most one level deep, and each extends the same base;
- neither file imports anything from a context's ``application.domain``;
- ``__init__.py`` exports exactly ``{Name}UseCase``, ``{Name}UseCaseInput`` and ``{Name}UseCaseOutput``.

``PENDING_PORTS`` lists the use cases not yet migrated, as ``"<context>/<aggregate>/<use_case>"``. It is a
literal on purpose: each migration deletes its lines, and a stale line fails ``test_pending_ports_exist``.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import pytest

from tests.architecture.contexts import context_dir, context_names

if TYPE_CHECKING:
    from pathlib import Path

INBOUND_PORT = ("application", "port", "inbound")
DOMAIN_MARKER = ".application.domain"

PENDING_PORTS: frozenset[str] = frozenset()


def _all_use_case_dirs() -> dict[str, Path]:
    """Return every use-case directory of every context, keyed ``"<context>/<aggregate>/<use_case>"``."""
    found: dict[str, Path] = {}
    for context in context_names():
        inbound = context_dir(context).joinpath(*INBOUND_PORT)
        for aggregate_dir in sorted(inbound.iterdir()):
            if not aggregate_dir.is_dir() or aggregate_dir.name == "__pycache__":
                continue
            for use_case_dir in sorted(aggregate_dir.iterdir()):
                if use_case_dir.is_dir() and use_case_dir.name != "__pycache__":
                    found[f"{context}/{aggregate_dir.name}/{use_case_dir.name}"] = use_case_dir
    return found


def _migrated() -> list[str]:
    return sorted(set(_all_use_case_dirs()) - PENDING_PORTS)


def _migrated_with_input() -> list[str]:
    dirs = _all_use_case_dirs()
    return [key for key in _migrated() if (dirs[key] / "input.py").is_file()]


def _prefix(key: str) -> str:
    """Return ``ListTableCommits`` for ``"<context>/<aggregate>/list_table_commits"``."""
    return "".join(word.capitalize() for word in key.rsplit("/", 1)[-1].split("_"))


def _extends_only(node: ast.ClassDef, base_name: str) -> bool:
    """Return whether ``node`` has exactly one base, the bare name ``base_name``, and no keywords."""
    return (
        len(node.bases) == 1
        and isinstance(node.bases[0], ast.Name)
        and node.bases[0].id == base_name
        and not node.keywords
        and not node.decorator_list
    )


def _imports_base_name(tree: ast.Module, base_name: str) -> bool:
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == "base"
        and not node.level
        and any(alias.name == base_name and alias.asname is None for alias in node.names)
        for node in ast.walk(tree)
    )


def _domain_imports(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names if DOMAIN_MARKER in f"{alias.name}.")
        elif isinstance(node, ast.ImportFrom) and node.level:
            found.append("." * node.level + (node.module or ""))
        elif isinstance(node, ast.ImportFrom) and node.module:
            if DOMAIN_MARKER in f"{node.module}.":
                found.append(node.module)
            else:
                found.extend(
                    f"{node.module}.{alias.name}"
                    for alias in node.names
                    if DOMAIN_MARKER in f"{node.module}.{alias.name}."
                )
    return found


def model_file_problems(source: str, expected_class: str, base_name: str) -> list[str]:
    """Return what is wrong with an ``input.py`` / ``output.py`` that should define ``expected_class``."""
    tree = ast.parse(source)
    problems: list[str] = []
    top_level = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    if [node.name for node in top_level] != [expected_class]:
        problems.append(f"defines top-level classes {[node.name for node in top_level]}, expected [{expected_class!r}]")
    if not _imports_base_name(tree, base_name):
        problems.append(f"does not import {base_name} from base")
    for top in top_level:
        if not _extends_only(top, base_name):
            problems.append(f"{top.name} must extend only {base_name}")
        for nested in (node for node in top.body if isinstance(node, ast.ClassDef)):
            if not _extends_only(nested, base_name):
                problems.append(f"{top.name}.{nested.name} must extend only {base_name}")
            deeper = [node.name for node in ast.walk(nested) if isinstance(node, ast.ClassDef) and node is not nested]
            if deeper:
                problems.append(f"{top.name}.{nested.name} nests {deeper}; one nesting level at most")
    problems.extend(f"imports {module}, a domain or relative module" for module in _domain_imports(tree))
    return problems


def exported_names(source: str) -> set[str] | None:
    """Return the names in an ``__init__.py``'s literal ``__all__``, or ``None`` when it has none."""
    for node in ast.parse(source).body:
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets)
            and isinstance(node.value, ast.List | ast.Tuple)
        ):
            return {
                element.value
                for element in node.value.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            }
    return None


def init_export_problems(source: str, prefix: str, *, has_input: bool) -> list[str]:
    """Return what is wrong with a use case's ``__init__.py``, which exports exactly its three names."""
    exported = exported_names(source)
    if exported is None:
        return ["has no literal __all__"]
    expected = {f"{prefix}UseCase", f"{prefix}UseCaseOutput"} | ({f"{prefix}UseCaseInput"} if has_input else set())
    problems: list[str] = []
    if missing := sorted(expected - exported):
        problems.append(f"does not export {missing}")
    if extra := sorted(exported - expected):
        problems.append(f"exports {extra} beyond the use case, its input and its output")
    return problems


def test_pending_ports_exist() -> None:
    """Every ``PENDING_PORTS`` entry is a real use-case directory, so a stale entry fails."""
    stale = sorted(PENDING_PORTS - set(_all_use_case_dirs()))
    assert stale == [], f"PENDING_PORTS lists use cases that do not exist: {stale}"


def test_use_case_scan_is_not_vacuous() -> None:
    """The scan finds use-case directories in every context, so a pass means something."""
    found = _all_use_case_dirs()
    assert {key.split("/", 1)[0] for key in found} == set(context_names())


@pytest.mark.parametrize("key", _migrated_with_input())
def test_input_is_one_use_case_input_model(key: str) -> None:
    """``input.py`` defines one ``{Name}UseCaseInput`` on ``UseCaseInput``, nested classes one level deep."""
    source = (_all_use_case_dirs()[key] / "input.py").read_text()
    assert model_file_problems(source, f"{_prefix(key)}UseCaseInput", "UseCaseInput") == []


@pytest.mark.parametrize("key", _migrated())
def test_output_is_one_use_case_output_model(key: str) -> None:
    """``output.py`` defines one ``{Name}UseCaseOutput`` on ``UseCaseOutput``, nested classes one level deep."""
    source = (_all_use_case_dirs()[key] / "output.py").read_text()
    assert model_file_problems(source, f"{_prefix(key)}UseCaseOutput", "UseCaseOutput") == []


@pytest.mark.parametrize("key", _migrated())
def test_init_exports_exactly_the_three_names(key: str) -> None:
    """``__init__.py`` exports the use case, its input (when it has one) and its output, nothing else."""
    use_case_dir = _all_use_case_dirs()[key]
    source = (use_case_dir / "__init__.py").read_text()
    assert init_export_problems(source, _prefix(key), has_input=(use_case_dir / "input.py").is_file()) == []


GOOD_OUTPUT = '''"""Define the ListWidgetsUseCaseOutput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseOutput


class ListWidgetsUseCaseOutput(UseCaseOutput):
    """Carry the widgets."""

    class Widget(UseCaseOutput):
        """One widget."""

        name: str
        made_at: datetime

    widgets: tuple[Widget, ...]
'''


def test_checker_accepts_a_migrated_output() -> None:
    """One top-level class on the base with one nested class on the same base passes."""
    assert model_file_problems(GOOD_OUTPUT, "ListWidgetsUseCaseOutput", "UseCaseOutput") == []


def test_checker_reports_a_dataclass() -> None:
    """A frozen dataclass is not a migrated port."""
    source = (
        "from dataclasses import dataclass\n\n\n@dataclass(frozen=True)\nclass ListWidgetsUseCaseOutput:\n"
        "    total: int\n"
    )
    assert model_file_problems(source, "ListWidgetsUseCaseOutput", "UseCaseOutput") == [
        "does not import UseCaseOutput from base",
        "ListWidgetsUseCaseOutput must extend only UseCaseOutput",
    ]


def test_checker_reports_a_second_top_level_class() -> None:
    """An ``…Item`` class beside the output must become a nested class."""
    source = GOOD_OUTPUT + "\n\nclass ListWidgetsUseCaseOutputItem(UseCaseOutput):\n    name: str\n"
    assert model_file_problems(source, "ListWidgetsUseCaseOutput", "UseCaseOutput") == [
        "defines top-level classes ['ListWidgetsUseCaseOutput', 'ListWidgetsUseCaseOutputItem'], "
        "expected ['ListWidgetsUseCaseOutput']",
    ]


def test_checker_reports_the_wrong_base() -> None:
    """An input on ``UseCaseOutput``, or a nested class on another base, is reported."""
    source = (
        "from base import UseCaseInput, ValueObject\n\n\nclass GetWidgetUseCaseInput(UseCaseInput):\n"
        "    class Filter(ValueObject):\n        key: str\n\n    uuid: str\n"
    )
    assert model_file_problems(source, "GetWidgetUseCaseInput", "UseCaseInput") == [
        "GetWidgetUseCaseInput.Filter must extend only UseCaseInput",
    ]
    assert "GetWidgetUseCaseInput must extend only UseCaseOutput" in model_file_problems(
        source, "GetWidgetUseCaseInput", "UseCaseOutput"
    )


def test_checker_reports_a_second_nesting_level() -> None:
    """A class nested inside a nested class is reported."""
    source = (
        "from base import UseCaseOutput\n\n\nclass GetWidgetUseCaseOutput(UseCaseOutput):\n"
        "    class Part(UseCaseOutput):\n        class Bolt(UseCaseOutput):\n            size: int\n\n"
        "        bolts: tuple[Bolt, ...]\n\n    parts: tuple[Part, ...]\n"
    )
    assert model_file_problems(source, "GetWidgetUseCaseOutput", "UseCaseOutput") == [
        "GetWidgetUseCaseOutput.Part nests ['Bolt']; one nesting level at most",
    ]


def test_checker_reports_a_domain_import() -> None:
    """A domain import is reported, also under ``TYPE_CHECKING``."""
    source = (
        "from typing import TYPE_CHECKING\n\nfrom base import UseCaseOutput\n\nif TYPE_CHECKING:\n"
        "    from context.widget.application.domain.model.widget import Widget\n\n\n"
        "class GetWidgetUseCaseOutput(UseCaseOutput):\n    name: str\n"
    )
    assert model_file_problems(source, "GetWidgetUseCaseOutput", "UseCaseOutput") == [
        "imports context.widget.application.domain.model.widget, a domain or relative module",
    ]


def test_exported_names_reads_the_literal_all() -> None:
    """``__all__`` is read as a set; a module without one gives ``None``."""
    assert exported_names('__all__ = ["GetWidgetUseCase", "GetWidgetUseCaseOutput"]\n') == {
        "GetWidgetUseCase",
        "GetWidgetUseCaseOutput",
    }
    assert exported_names("from x import y\n") is None


def test_checker_reports_the_domain_package_imported_by_name() -> None:
    """``from context.x.application import domain`` reaches the domain too, so it is reported."""
    source = (
        "from base import UseCaseOutput\nfrom context.widget.application import domain\n\n\n"
        "class GetWidgetUseCaseOutput(UseCaseOutput):\n    name: str\n"
    )
    assert model_file_problems(source, "GetWidgetUseCaseOutput", "UseCaseOutput") == [
        "imports context.widget.application.domain, a domain or relative module",
    ]


def test_init_checker_accepts_exactly_the_three_names() -> None:
    """An ``__init__.py`` exporting the use case, its input and its output passes."""
    source = '__all__ = ["GetWidgetUseCase", "GetWidgetUseCaseInput", "GetWidgetUseCaseOutput"]\n'
    assert init_export_problems(source, "GetWidget", has_input=True) == []


def test_init_checker_reports_an_extra_item_export() -> None:
    """An ``…Item`` export left beside the three names is reported."""
    source = (
        '__all__ = ["ListWidgetsUseCase", "ListWidgetsUseCaseInput", "ListWidgetsUseCaseOutput", '
        '"ListWidgetsUseCaseOutputItem"]\n'
    )
    assert init_export_problems(source, "ListWidgets", has_input=True) == [
        "exports ['ListWidgetsUseCaseOutputItem'] beyond the use case, its input and its output",
    ]


def test_init_checker_reports_a_missing_name_and_a_missing_all() -> None:
    """A missing export, or no literal ``__all__``, is reported."""
    assert init_export_problems('__all__ = ["GetWidgetUseCase"]\n', "GetWidget", has_input=False) == [
        "does not export ['GetWidgetUseCaseOutput']",
    ]
    assert init_export_problems("from x import y\n", "GetWidget", has_input=False) == ["has no literal __all__"]
