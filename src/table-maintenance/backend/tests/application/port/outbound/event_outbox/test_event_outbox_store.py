"""Tests for EventOutboxStore port interface."""

from __future__ import annotations

from base.store import Store

from application.port.outbound.event_outbox.event_outbox_store import EventOutboxStore


def test_is_store() -> None:
    """EventOutboxStore extends Store."""
    assert issubclass(EventOutboxStore, Store)


def test_declares_save() -> None:
    """EventOutboxStore defines save."""
    assert hasattr(EventOutboxStore, "save")


def test_declares_fetch_unpublished() -> None:
    """EventOutboxStore defines fetch_unpublished."""
    assert hasattr(EventOutboxStore, "fetch_unpublished")


def test_declares_mark_published() -> None:
    """EventOutboxStore defines mark_published."""
    assert hasattr(EventOutboxStore, "mark_published")
