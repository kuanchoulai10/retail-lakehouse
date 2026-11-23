"""Define ReadOnlyMapping, the type of a domain model field that holds a mapping."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, MutableSequence, MutableSet
from typing import TYPE_CHECKING, Annotated, Any, NoReturn, Self, get_args

from pydantic_core import core_schema

if TYPE_CHECKING:
    from pydantic import GetCoreSchemaHandler


class _FrozenDict(dict):
    """A dict no one can edit in place; it still encodes as JSON and passes a strict ``dict`` field."""

    __slots__ = ()

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:  # noqa: ANN401
        """Build from what ``dict(...)`` accepts, freezing every value, so ``type(m)(pairs)`` rebuilds one."""
        self = super().__new__(cls)
        dict.update(self, {key: _frozen(value) for key, value in dict(*args, **kwargs).items()})
        return self

    def __init__(self, *_: object, **__: object) -> None:
        """Do nothing: the items are set once, by ``__new__``, so calling ``__init__`` again changes nothing."""

    def _refuse(self, *_: object, **__: object) -> NoReturn:
        raise TypeError("ReadOnlyMapping is read-only: assign a new mapping to the field instead")

    __setitem__ = __delitem__ = __ior__ = _refuse
    update = pop = popitem = clear = setdefault = _refuse

    def __eq__(self, other: object) -> bool:
        """Compare items with any mapping; a frozen tuple equals the list it was built from."""
        if not isinstance(other, Mapping):
            return NotImplemented
        return _thawed(self) == _thawed(other)

    def __ne__(self, other: object) -> bool:
        """Negate ``__eq__``."""
        equal = self.__eq__(other)
        return equal if equal is NotImplemented else not equal

    def __hash__(self) -> int:
        """Hash by the items, so equal mappings hash alike."""
        return hash(frozenset(self.items()))

    def __repr__(self) -> str:
        """Show the field type and the items."""
        return f"ReadOnlyMapping({dict(self)!r})"

    def __reduce__(self) -> tuple[type[_FrozenDict], tuple[dict[Any, Any]]]:
        """Rebuild from the items, which ``copy``, ``deepcopy`` and ``pickle`` use."""
        return (type(self), (dict(self),))


class _ReadOnly:
    """The Pydantic schema of ``ReadOnlyMapping``: validate as ``dict[K, V]``, freeze, dump plain."""

    def __get_pydantic_core_schema__(self, source: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:  # noqa: ANN401
        """Validate as ``dict[K, V]``, then freeze; dump as plain dicts and lists."""
        key, value = get_args(source) or (Any, Any)
        as_dict = handler.generate_schema(dict[key, value])
        return core_schema.no_info_after_validator_function(
            _FrozenDict,
            as_dict,
            serialization=core_schema.plain_serializer_function_ser_schema(_thawed),
        )


type ReadOnlyMapping[K, V] = Annotated[Mapping[K, V], _ReadOnly()]
"""A mapping field no one can edit in place, so a model changes it only by assigning a new one.

A field annotated ``ReadOnlyMapping[K, V]`` accepts a dict, validates its keys and values as
``dict[K, V]`` would, and holds the result read-only: editing it in place raises ``TypeError``,
and type checkers see a ``Mapping``, which has no editing methods. Dicts and lists inside the
values are frozen too (lists become tuples, sets frozensets; other mutable collections are
refused), and a frozen tuple still equals the list it came from. Dumping gives plain dicts and lists. It equals any
dict with the same items, hashes when its values do, and survives ``copy``, ``deepcopy`` and
``pickle``. Python 3.15's builtin ``frozendict`` can replace the frozen type once the backend
runs on 3.15.
"""


def _frozen(value: Any) -> Any:  # noqa: ANN401
    """Freeze dicts into read-only mappings, lists and tuples into tuples and sets into frozensets, all the way down.

    Any other mutable collection is refused, so nothing inside the mapping can be edited in place.
    """
    if isinstance(value, _FrozenDict):
        return value
    if isinstance(value, dict):
        return _FrozenDict(value)
    if isinstance(value, list | tuple):
        return tuple(_frozen(item) for item in value)
    if isinstance(value, set | frozenset):
        return frozenset(value)
    if isinstance(value, MutableMapping | MutableSequence | MutableSet | bytearray):
        msg = f"ReadOnlyMapping cannot hold a {type(value).__name__}: use a dict, list, tuple or set"
        raise ValueError(msg)  # noqa: TRY004
    return value


def _thawed(value: Any) -> Any:  # noqa: ANN401
    """Turn a mapping into a dict and a tuple into a list, all the way down."""
    if isinstance(value, Mapping):
        return {key: _thawed(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_thawed(item) for item in value]
    if isinstance(value, frozenset):
        return set(value)
    return value
