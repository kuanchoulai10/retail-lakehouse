"""Temporal activities are grouped by the workflow that calls them.

Each workflow contract package names its activities in one ``XActivity`` enum
(``contracts/<workflow>/activity.py``), and one ``XActivities`` class in
``inbound/activities/`` holds every method decorated with a member of that enum.
Each method wraps exactly one inbound port, except the signal wiring that talks
to the Temporal client instead.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.architecture.contexts import context_dir, context_names

_TEMPORAL = Path("adapter") / "hybrid" / "temporal"
_ACTIVITIES = _TEMPORAL / "inbound" / "activities"
_CONTRACTS = _TEMPORAL / "contracts"
_ENUM_SUFFIX = "Activity"
_CLASS_SUFFIX = "Activities"

SIGNAL_EXCEPTIONS = {"SIGNAL_ADMISSION_ACQUIRE", "SIGNAL_PARENT", "GET_WORKFLOW_RUNNING"}


@dataclass(frozen=True)
class DecoratedActivity:
    """One ``@activity.defn(name=<Enum>.<MEMBER>)`` method and the class it sits in."""

    module: str
    owner: str
    method: str
    enum: str
    member: str
    port_calls: int


def _temporal_contexts() -> list[str]:
    return [name for name in context_names() if (context_dir(name) / _ACTIVITIES).is_dir()]


def _activity_name(decorator: ast.expr) -> tuple[str, str] | None:
    """Return ``(enum, member)`` of an ``activity.defn(name=Enum.MEMBER)`` decorator."""
    if not (
        isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Attribute)
        and decorator.func.attr == "defn"
        and isinstance(decorator.func.value, ast.Name)
        and decorator.func.value.id == "activity"
    ):
        return None
    for keyword in decorator.keywords:
        value = keyword.value
        if keyword.arg == "name" and isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name):
            return value.value.id, value.attr
    return None


def _port_calls(method: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count the ``self._<port>.execute(...)`` calls in ``method``."""
    return sum(
        1
        for node in ast.walk(method)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "execute"
        and isinstance(node.func.value, ast.Attribute)
        and node.func.value.attr.startswith("_")
        and isinstance(node.func.value.value, ast.Name)
        and node.func.value.value.id == "self"
    )


def decorated_activities(activities_dir: Path) -> list[DecoratedActivity]:
    """Return every decorated activity method of the modules in ``activities_dir``."""
    found: list[DecoratedActivity] = []
    for path in sorted(activities_dir.glob("*.py")):
        tree = ast.parse(path.read_text())
        for owner in (node for node in tree.body if isinstance(node, ast.ClassDef)):
            for method in owner.body:
                if not isinstance(method, ast.FunctionDef | ast.AsyncFunctionDef):
                    continue
                for decorator in method.decorator_list:
                    name = _activity_name(decorator)
                    if name is not None:
                        found.append(DecoratedActivity(path.stem, owner.name, method.name, *name, _port_calls(method)))
    return found


def activities_classes(activities_dir: Path) -> set[str]:
    """Return the top-level ``*Activities`` classes of the modules in ``activities_dir``."""
    return {
        node.name
        for path in activities_dir.glob("*.py")
        for node in ast.parse(path.read_text()).body
        if isinstance(node, ast.ClassDef) and node.name.endswith(_CLASS_SUFFIX)
    }


def activity_enums(contracts_dir: Path) -> set[str]:
    """Return the ``*Activity`` enums declared in ``contracts/*/activity.py``."""
    return {
        node.name
        for path in contracts_dir.glob("*/activity.py")
        for node in ast.parse(path.read_text()).body
        if isinstance(node, ast.ClassDef) and node.name.endswith(_ENUM_SUFFIX)
    }


def _class_for(enum: str) -> str:
    return enum.removesuffix(_ENUM_SUFFIX) + _CLASS_SUFFIX


def misplaced_activities(activities_dir: Path) -> list[str]:
    """Return each decorated method that does not sit in the class of its activity enum."""
    return [
        f"{found.module}.{found.owner}.{found.method} ({found.enum}.{found.member}) belongs in {_class_for(found.enum)}"
        for found in decorated_activities(activities_dir)
        if found.owner != _class_for(found.enum)
    ]


def port_call_violations(activities_dir: Path) -> list[str]:
    """Return each activity that calls other than one inbound port, or a signal activity that calls one."""
    return [
        f"{found.owner}.{found.method} ({found.member}) calls {found.port_calls} inbound ports"
        for found in decorated_activities(activities_dir)
        if found.port_calls != (0 if found.member in SIGNAL_EXCEPTIONS else 1)
    ]


@pytest.mark.parametrize("context", _temporal_contexts())
def test_activity_lives_in_its_workflows_class(context: str):
    """Every activity sits in the activities class of the workflow whose enum names it."""
    assert misplaced_activities(context_dir(context) / _ACTIVITIES) == []


@pytest.mark.parametrize("context", _temporal_contexts())
def test_activity_calls_one_inbound_port(context: str):
    """Every activity wraps exactly one inbound port, except the signal wiring, which calls none."""
    assert port_call_violations(context_dir(context) / _ACTIVITIES) == []


@pytest.mark.parametrize("context", _temporal_contexts())
def test_one_activities_class_per_activity_enum(context: str):
    """There is exactly one activities class for each workflow activity enum, and no other."""
    root = context_dir(context)
    expected = {_class_for(enum) for enum in activity_enums(root / _CONTRACTS)}
    assert activities_classes(root / _ACTIVITIES) == expected


def test_signal_exceptions_name_real_activities():
    """Every exempted name is an activity some activities class still declares."""
    members = {
        found.member
        for context in _temporal_contexts()
        for found in decorated_activities(context_dir(context) / _ACTIVITIES)
    }
    assert members >= SIGNAL_EXCEPTIONS


_MISPLACED = """
from temporalio import activity


class TableReconciliationActivities:
    def __init__(self, *, submit):
        self._submit = submit

    @activity.defn(name=TableMaintenanceActivity.SUBMIT_MAINTENANCE_OPERATION)
    def submit_maintenance_operation(self, request):
        self._submit.execute(request)
        return self._submit.execute(request)

    @activity.defn(name=TableMaintenanceActivity.SIGNAL_PARENT)
    async def signal_parent(self, request):
        return None
"""


def test_scan_catches_a_method_in_another_workflows_class(tmp_path: Path):
    """A maintenance activity in the reconciliation class is reported with the class it belongs in."""
    (tmp_path / "table_reconciliation_activities.py").write_text(_MISPLACED)
    assert misplaced_activities(tmp_path) == [
        "table_reconciliation_activities.TableReconciliationActivities.submit_maintenance_operation "
        "(TableMaintenanceActivity.SUBMIT_MAINTENANCE_OPERATION) belongs in TableMaintenanceActivities",
        "table_reconciliation_activities.TableReconciliationActivities.signal_parent "
        "(TableMaintenanceActivity.SIGNAL_PARENT) belongs in TableMaintenanceActivities",
    ]


def test_scan_counts_the_inbound_port_calls(tmp_path: Path):
    """An activity calling its port twice is reported; a signal activity calling none is not."""
    (tmp_path / "table_reconciliation_activities.py").write_text(_MISPLACED)
    assert port_call_violations(tmp_path) == [
        "TableReconciliationActivities.submit_maintenance_operation (SUBMIT_MAINTENANCE_OPERATION) "
        "calls 2 inbound ports"
    ]
