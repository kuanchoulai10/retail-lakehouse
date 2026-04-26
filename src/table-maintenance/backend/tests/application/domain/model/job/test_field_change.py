"""Tests for FieldChange value object."""

from base import ValueObject
from core.application.domain.model.job.field_change import FieldChange


def test_is_value_object():
    """Verify FieldChange is a ValueObject subclass."""
    assert issubclass(FieldChange, ValueObject)


def test_fields():
    """Verify FieldChange stores field, old_value, new_value."""
    fc = FieldChange(field="cron", old_value="0 * * * *", new_value="0 2 * * *")
    assert fc.field == "cron"
    assert fc.old_value == "0 * * * *"
    assert fc.new_value == "0 2 * * *"


def test_equality_by_value():
    """Verify two FieldChanges with same values are equal."""
    a = FieldChange(field="cron", old_value=None, new_value="0 2 * * *")
    b = FieldChange(field="cron", old_value=None, new_value="0 2 * * *")
    assert a == b


def test_none_values_allowed():
    """Verify old_value and new_value can be None."""
    fc = FieldChange(field="cron", old_value=None, new_value=None)
    assert fc.old_value is None
    assert fc.new_value is None
