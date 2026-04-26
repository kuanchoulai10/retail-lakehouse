"""Tests for EventOutboxRepo port interface."""

from abc import ABC

from application.port.outbound.event_outbox_repo import EventOutboxRepo


def test_is_abstract():
    """Verify EventOutboxRepo is an ABC."""
    assert issubclass(EventOutboxRepo, ABC)


def test_has_save_method():
    """Verify EventOutboxRepo defines save."""
    assert hasattr(EventOutboxRepo, "save")


def test_has_fetch_unpublished_method():
    """Verify EventOutboxRepo defines fetch_unpublished."""
    assert hasattr(EventOutboxRepo, "fetch_unpublished")


def test_has_mark_published_method():
    """Verify EventOutboxRepo defines mark_published."""
    assert hasattr(EventOutboxRepo, "mark_published")
