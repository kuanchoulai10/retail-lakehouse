"""Tests for the WholeSeconds duration type."""

from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from base.model import WholeSeconds


class _Timeout(BaseModel):
    """A strict model carrying one WholeSeconds field."""

    model_config = ConfigDict(strict=True)

    duration: WholeSeconds


def test_accepts_a_timedelta() -> None:
    """A ``timedelta`` passes through."""
    assert _Timeout(duration=timedelta(minutes=1)).duration == timedelta(minutes=1)


def test_accepts_int_seconds() -> None:
    """An int is read as seconds."""
    assert _Timeout.model_validate({"duration": 90}).duration == timedelta(seconds=90)


def test_accepts_int_seconds_from_json() -> None:
    """A JSON integer is read as seconds."""
    assert _Timeout.model_validate_json('{"duration": 90}').duration == timedelta(seconds=90)


@pytest.mark.parametrize("value", [True, 1.5, "90"])
def test_rejects_a_non_int(value: object) -> None:
    """A bool, a float or a string is rejected."""
    with pytest.raises(ValidationError):
        _Timeout.model_validate({"duration": value})


def test_rejects_a_bool_from_json() -> None:
    """A JSON ``true`` is rejected."""
    with pytest.raises(ValidationError):
        _Timeout.model_validate_json('{"duration": true}')


def test_serializes_to_int_seconds_in_json_mode() -> None:
    """JSON mode writes whole seconds as an int."""
    assert _Timeout(duration=timedelta(hours=1)).model_dump(mode="json") == {"duration": 3600}


def test_stays_a_timedelta_in_python_mode() -> None:
    """Python mode keeps the ``timedelta``."""
    assert _Timeout(duration=timedelta(hours=1)).model_dump() == {"duration": timedelta(hours=1)}


def test_serializing_a_fractional_second_raises() -> None:
    """A duration that is not whole seconds cannot be written."""
    with pytest.raises(ValueError, match="whole number of seconds"):
        _Timeout(duration=timedelta(milliseconds=1500)).model_dump(mode="json")


def test_serializing_a_huge_duration_keeps_its_microseconds() -> None:
    """A very large duration with a stray microsecond is rejected, not rounded away by float seconds."""
    with pytest.raises(ValueError, match="whole number of seconds"):
        _Timeout(duration=timedelta(days=10**6, microseconds=1)).model_dump(mode="json")


def test_serializes_a_huge_whole_duration_exactly() -> None:
    """A very large whole duration is written exactly."""
    assert _Timeout(duration=timedelta(days=10**6)).model_dump(mode="json") == {"duration": 10**6 * 86400}
