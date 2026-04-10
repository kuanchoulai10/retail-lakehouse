"""Tests for UseCase base type."""

import pytest
from base import UseCase


def test_use_case_is_abstract():
    with pytest.raises(TypeError):
        UseCase()  # type: ignore[call-arg]


def test_use_case_requires_execute():
    """UseCase subclass without execute() cannot be instantiated."""

    class Incomplete(UseCase[str, str]):
        pass

    with pytest.raises(TypeError):
        Incomplete()  # type: ignore[abstract]


def test_use_case_execute():
    """Concrete UseCase can be instantiated and executed."""

    class Greet(UseCase[str, str]):
        def execute(self, request: str) -> str:
            return f"Hello, {request}!"

    result = Greet().execute("World")
    assert result == "Hello, World!"


def test_use_case_none_output():
    """UseCase with None output works as a command."""
    side_effects: list[str] = []

    class LogMessage(UseCase[str, None]):
        def execute(self, request: str) -> None:
            side_effects.append(request)

    LogMessage().execute("logged")
    assert side_effects == ["logged"]
