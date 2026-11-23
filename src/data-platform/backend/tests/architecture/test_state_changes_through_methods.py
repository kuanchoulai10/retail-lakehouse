"""Guard test: an aggregate changes only through its own methods, in every layer of every context.

An aggregate keeps its invariants only if every change goes through a method of its own, so no
other code (domain services, other aggregates, application services, ports, adapters) assigns or
deletes an attribute of an object it holds (``table.status = …``, ``run.attempts += …``,
``run.attempts[0] = …``), calls another object's private method (``table._assign_together(…)``),
or writes one reflectively (``setattr(table, …)``, ``object.__setattr__(…)``, ``table.__dict__``,
``vars(table)``, ``model_copy(update=…)``, ``model_construct(…)``). Assigning its own attributes
(``self._repo = repo``), calling its own class's private helpers (``Schema._walk``,
``type(self)._clamp``) and Starlette's ``app.state`` are allowed. An object built in the same
function is another object too: build it with its values in one call. The collections inside an
aggregate cannot be edited in place at all (``test_domain_collections_are_immutable.py``).
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import pytest

from tests.architecture.contexts import BACKEND, context_dir, context_names

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

_OWN = frozenset({"self", "cls"})
_STARLETTE_CONNECTIONS = frozenset({"request", "websocket"})


def _is_foreign(target: ast.expr) -> bool:
    """Tell whether ``target`` is an attribute, or an item of an attribute, of something other than ``self`` or ``cls``.

    The attribute's direct owner counts, so ``self.run.status`` is another object's attribute
    reached through ``self``; ``self.items[0]`` is an item of the object's own attribute.
    """
    node: ast.expr = target
    while isinstance(node, ast.Subscript):
        node = node.value
    if not isinstance(node, ast.Attribute):
        return False
    if _is_app_state(node.value):
        return False
    return not (isinstance(node.value, ast.Name) and node.value.id in _OWN)


def _is_app_state(owner: ast.expr) -> bool:
    """Tell whether ``owner`` is Starlette's ``app.state``: ``app.state`` or ``request.app.state``."""
    if not (isinstance(owner, ast.Attribute) and owner.attr == "state"):
        return False
    app = owner.value
    if isinstance(app, ast.Name):
        return app.id == "app"
    return (
        isinstance(app, ast.Attribute)
        and app.attr == "app"
        and isinstance(app.value, ast.Name)
        and app.value.id in _STARLETTE_CONNECTIONS
    )


def foreign_assignments(source: str) -> list[str]:
    """Return ``<line>: <target>`` for each assignment or deletion of another object's attribute.

    Every target counts, wherever it is bound: an assignment, ``del``, ``for``, ``with … as`` or a
    comprehension.
    """
    targets = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Attribute | ast.Subscript) and isinstance(node.ctx, ast.Store | ast.Del)
    ]
    return [
        f"{node.lineno}: {ast.unparse(node)}"
        for node in sorted(targets, key=lambda n: (n.lineno, n.col_offset))
        if _is_foreign(node)
    ]


def _is_private(name: str) -> bool:
    return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))


def _is_own(receiver: ast.expr) -> bool:
    if isinstance(receiver, ast.Name):
        return receiver.id in _OWN
    return isinstance(receiver, ast.Call) and isinstance(receiver.func, ast.Name) and receiver.func.id == "super"


def _is_own_class(receiver: ast.expr, classes: tuple[str, ...]) -> bool:
    """Tell whether ``receiver`` names an enclosing class, or is ``type(self)``."""
    if isinstance(receiver, ast.Name):
        return receiver.id in classes
    return (
        isinstance(receiver, ast.Call)
        and isinstance(receiver.func, ast.Name)
        and receiver.func.id == "type"
        and len(receiver.args) == 1
        and isinstance(receiver.args[0], ast.Name)
        and receiver.args[0].id == "self"
    )


def _calls_with_classes(node: ast.AST, classes: tuple[str, ...] = ()) -> Iterator[tuple[ast.Call, tuple[str, ...]]]:
    """Yield every call under ``node`` with the names of the classes enclosing it."""
    if isinstance(node, ast.ClassDef):
        classes = (*classes, node.name)
    if isinstance(node, ast.Call):
        yield node, classes
    for child in ast.iter_child_nodes(node):
        yield from _calls_with_classes(child, classes)


def foreign_private_calls(source: str) -> list[str]:
    """Return ``<line>: <call>`` for each call of a private method on another object.

    ``self``, ``cls``, ``super()``, an enclosing class by name and ``type(self)`` are the code's own.
    """
    return [
        f"{node.lineno}: {ast.unparse(node.func)}"
        for node, classes in _calls_with_classes(ast.parse(source))
        if isinstance(node.func, ast.Attribute)
        and _is_private(node.func.attr)
        and not _is_own(node.func.value)
        and not (classes and _is_own_class(node.func.value, classes))
    ]


_REFLECTIVE_FUNCTIONS = frozenset({"setattr", "delattr", "vars"})
_WRITERS = frozenset({"setattr", "delattr"})
_REFLECTIVE_DUNDERS = frozenset(
    {
        "__setattr__",
        "__delattr__",
        "__setitem__",
        "__delitem__",
        "__init__",
        "__setstate__",
        "__replace__",
        "__ior__",
        "__getattribute__",
    }
)
_BUILTIN_TYPES = frozenset({"object", "type", "dict", "list", "set", "bytearray", "BaseModel"})
_BUILTIN_TYPE_READS = frozenset({"fromkeys"})
_REPLACE_MODULES = frozenset({"copy", "dataclasses"})


def _is_self_or_cls(node: ast.expr) -> bool:
    return isinstance(node, ast.Name) and node.id in _OWN


def _is_private_literal(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("_")


def _is_reflective_write(node: ast.AST, parent: ast.AST | None) -> bool:
    if isinstance(node, ast.Attribute):
        return (node.attr == "__dict__" and not _is_self_or_cls(node.value)) or node.attr in _WRITERS
    if isinstance(node, ast.Name):
        return node.id in _WRITERS and not (isinstance(parent, ast.Call) and parent.func is node)
    if isinstance(node, ast.ImportFrom):
        return node.module in _REPLACE_MODULES and any(alias.name == "replace" for alias in node.names)
    return isinstance(node, ast.Call) and _is_reflective_call(node)


def _is_reflective_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Name):
        return _is_reflective_function_call(func.id, node.args)
    if not isinstance(func, ast.Attribute):
        return False
    receiver = func.value
    if isinstance(receiver, ast.Name) and receiver.id in _BUILTIN_TYPES | _REPLACE_MODULES:
        return _is_module_or_type_write(receiver.id, func.attr)
    if func.attr in _REFLECTIVE_DUNDERS:
        return not _is_own(receiver)
    if func.attr == "model_copy":
        return any(keyword.arg == "update" for keyword in node.keywords)
    return func.attr == "model_construct"


def _is_module_or_type_write(owner: str, method: str) -> bool:
    if owner in _REPLACE_MODULES:
        return method == "replace"
    return method not in _BUILTIN_TYPE_READS


def _is_reflective_function_call(name: str, args: list[ast.expr]) -> bool:
    if name in _REFLECTIVE_FUNCTIONS:
        return bool(args) and not _is_self_or_cls(args[0])
    if name == "getattr":
        return len(args) >= 2 and not _is_self_or_cls(args[0]) and _is_private_literal(args[1])  # noqa: PLR2004
    return False


def reflective_writes(source: str) -> list[str]:
    """Return ``<line>: <code>`` for each reflective write to another object.

    Flagged: ``setattr`` / ``delattr`` / ``vars`` on anything but ``self`` or ``cls``, and any other
    use of ``setattr`` / ``delattr`` (bound to a name, passed to ``partial``, ``builtins.setattr``);
    ``getattr`` of a private or dunder name on another object; a call of ``__setattr__``,
    ``__delattr__``, ``__setitem__``, ``__delitem__``, ``__init__``, ``__setstate__``, ``__replace__``,
    ``__ior__`` or ``__getattribute__`` on anything but ``self``, ``cls`` or ``super()``; any method
    called through a builtin type or ``BaseModel`` (``dict.update(m, …)``, ``object.__setattr__(…)``),
    except ``dict.fromkeys``; another object's ``__dict__``; ``copy.replace`` and
    ``dataclasses.replace`` (and importing either); ``model_copy(update=…)`` and ``model_construct(…)``,
    which skip validation.
    """
    tree = ast.parse(source)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    return [
        f"{node.lineno}: {ast.unparse(node)}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute | ast.Name | ast.Call | ast.ImportFrom)
        and _is_reflective_write(node, parents.get(node))
    ]


_LAYERS = (
    ("application", "domain", "model"),
    ("application", "domain", "service"),
    ("application", "port"),
    ("application", "service"),
    ("adapter",),
)


def _scanned_files() -> list[Path]:
    files: list[Path] = []
    for name in context_names():
        files += [p for p in context_dir(name).rglob("*.py") if "__pycache__" not in p.parts]
    return sorted(files)


_FILES = _scanned_files()
_IDS = [str(p.relative_to(BACKEND)) for p in _FILES]


@pytest.mark.parametrize("path", _FILES, ids=_IDS)
def test_context_code_assigns_only_its_own_attributes(path: Path) -> None:
    """Context code assigns or deletes only its own attributes, never those of an object it holds."""
    found = foreign_assignments(path.read_text())
    assert not found, f"{path.relative_to(BACKEND)} changes another object's state: {found}"


@pytest.mark.parametrize("path", _FILES, ids=_IDS)
def test_context_code_calls_no_private_method_of_another_object(path: Path) -> None:
    """Context code calls private methods only on itself or its own class, never on an object it holds."""
    found = foreign_private_calls(path.read_text())
    assert not found, f"{path.relative_to(BACKEND)} calls another object's private method: {found}"


@pytest.mark.parametrize("path", _FILES, ids=_IDS)
def test_context_code_makes_no_reflective_write(path: Path) -> None:
    """Context code never changes another object through ``setattr``, ``__dict__`` or an unvalidated copy."""
    found = reflective_writes(path.read_text())
    assert not found, f"{path.relative_to(BACKEND)} writes another object's state reflectively: {found}"


def test_the_scan_covers_every_layer_of_every_context() -> None:
    """Every layer of every context is scanned: domain model and services, ports, services and adapters."""
    for name in context_names():
        root = context_dir(name)
        for layer in _LAYERS:
            assert any(p.is_relative_to(root.joinpath(*layer)) for p in _FILES), (name, layer)


@pytest.mark.parametrize(
    "source",
    [
        "table.status = x",
        "run.attempts += (a,)",
        "a.b.c = 1",
        "run.attempts[0] = a",
        "del table.priority",
        "table.priority: str = 'P1'",
        "x, table.status = 1, 2",
        "self.repo.table.status = x",
        "for table.status in xs:\n    pass",
        "with cm() as table.status:\n    pass",
        "[0 for table.status in xs]",
    ],
)
def test_the_assignment_check_flags_another_objects_attributes(source: str) -> None:
    """Assigning, extending or deleting an attribute of anything but ``self`` or ``cls`` is flagged."""
    assert foreign_assignments(source)


@pytest.mark.parametrize(
    "source",
    ["self._repo = repo", "cls.count = 1", "x = 1", "rows[0] = r", "app.state.use_cases = u", "self.items[0] = a"],
)
def test_the_assignment_check_allows_own_and_local_state(source: str) -> None:
    """Own attributes, local names and their items, and ``app.state`` are allowed."""
    assert foreign_assignments(source) == []


@pytest.mark.parametrize(
    ("source", "flagged"),
    [
        ("app.state.x = 1", False),
        ("request.app.state.x = 1", False),
        ("table.state.status = x", True),
        ("run.state.flag = 1", True),
        ("table.app.state.flag = 1", True),
    ],
)
def test_the_assignment_check_allows_only_starlettes_app_state(source: str, *, flagged: bool) -> None:
    """Only Starlette's ``app.state`` may be assigned; another object's ``state`` attribute may not."""
    assert bool(foreign_assignments(source)) is flagged


def test_an_attribute_write_on_a_locally_built_object_is_flagged() -> None:
    """An object built in the function is still another object: build it with its values in one call."""
    assert foreign_assignments("def f():\n    b = Builder()\n    b.x = 1\n") == ["3: b.x"]


def test_the_assignment_check_names_the_line_and_the_target() -> None:
    """A finding names its line and the target as written."""
    assert foreign_assignments("x = 1\nrun.attempts[0] = a\n") == ["2: run.attempts[0]"]


@pytest.mark.parametrize("source", ["t._assign_together(id=x)", "repo.table._set(1)", "make()._f()"])
def test_the_call_check_flags_another_objects_private_methods(source: str) -> None:
    """A private method called on anything but ``self``, ``cls`` or ``super()`` is flagged."""
    assert foreign_private_calls(source)


@pytest.mark.parametrize("source", ["self._f()", "cls._g()", "super()._f()", "t.__init__()", "t.public()", "_f()"])
def test_the_call_check_allows_own_private_and_public_calls(source: str) -> None:
    """Own private calls, dunders, public methods and plain functions are allowed."""
    assert foreign_private_calls(source) == []


@pytest.mark.parametrize(
    "source",
    [
        "class Schema:\n    def f(self):\n        return Schema._walk(1)\n",
        "class Run:\n    def f(self):\n        return type(self)._clamp(1)\n",
        "class Outer:\n    class Inner:\n        def f(self):\n            return Outer._walk(1)\n",
    ],
)
def test_a_class_may_call_its_own_private_helpers(source: str) -> None:
    """A class calls its own private static helpers by its own name or through ``type(self)``."""
    assert foreign_private_calls(source) == []


@pytest.mark.parametrize(
    "source",
    [
        "class Other:\n    def f(self):\n        return Schema._walk(1)\n",
        "Schema._walk(1)\n",
        "def f(t):\n    return type(t)._clamp(1)\n",
        "class Run:\n    @classmethod\n    def f(cls):\n        return type(cls)._clamp(1)\n",
        "class Schema:\n    pass\n\n\ndef f():\n    return Schema._walk(1)\n",
    ],
)
def test_another_class_or_module_code_calling_a_private_helper_is_flagged(source: str) -> None:
    """A private helper of a class called from another class or from module code is flagged."""
    assert foreign_private_calls(source)


@pytest.mark.parametrize(
    "source",
    [
        'setattr(table, "status", x)',
        'delattr(table, "status")',
        'object.__setattr__(table, "status", x)',
        'object.__delattr__(table, "status")',
        'object.__setattr__(self, "status", x)',
        'table.__setattr__("status", x)',
        'dict.__setitem__(table.properties, "k", "v")',
        'table.properties.__delitem__("k")',
        'table.__dict__["status"] = x',
        "table.__dict__.update(status=x)",
        'vars(table)["status"] = x',
        'table.model_copy(update={"status": x})',
        "Table.model_construct(status=x)",
        "dict.update(table.properties, k=1)",
        'dict.pop(table.properties, "k")',
        "dict.clear(table.properties)",
        "dict.__ior__(table.properties, {})",
        "list.append(rows, 1)",
        'object.__getattribute__(table, "__dict__")',
        "BaseModel.__init__(table, **data)",
        "table.__init__(**data)",
        "table.properties.__init__({})",
        "table.__setstate__(state)",
        "table.__replace__(status=x)",
        "copy.replace(table, status=x)",
        "dataclasses.replace(table, status=x)",
        "from copy import replace",
        "from dataclasses import replace as swap",
        'builtins.setattr(table, "s", 1)',
        "f = setattr",
        "partial(setattr, table)",
        "functools.partial(delattr, table)",
        'getattr(table, "__dict__")["s"] = 1',
        'getattr(table, "_assign_together")(status=x)',
    ],
)
def test_the_reflective_check_flags_bypasses(source: str) -> None:
    """Writing another object's state through ``setattr``, ``__dict__``, a dunder or an unvalidated copy is flagged."""
    assert reflective_writes(source)


@pytest.mark.parametrize(
    "source",
    [
        'setattr(self, "x", 1)',
        'setattr(cls, "x", 1)',
        "self.__dict__.update(x=1)",
        "super().__setattr__(name, value)",
        "table.model_copy()",
        "table.model_copy(deep=True)",
        'getattr(table, "status")',
        "vars()",
        "vars(self)",
        "dict.fromkeys(ids)",
        "super().__init__(**data)",
        'getattr(table, "status", None)',
        "getattr(self, name)",
        'getattr(self, "_x")',
        "policy.replace(content, now)",
        "text.replace('a', 'b')",
        "replace()",
    ],
)
def test_the_reflective_check_allows_own_and_plain_calls(source: str) -> None:
    """Own reflective writes, ``super()`` dunders, plain copies and reads are allowed."""
    assert reflective_writes(source) == []


def test_the_reflective_check_names_the_line_and_the_call() -> None:
    """A finding names its line and the call as written."""
    assert reflective_writes('x = 1\nsetattr(t, "a", 1)\n') == ["2: setattr(t, 'a', 1)"]
