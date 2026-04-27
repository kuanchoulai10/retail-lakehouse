"""Tests for SubmitJobRunGateway."""

from __future__ import annotations

from base.gateway import Gateway

from application.port.outbound.job_run.submit_job_run.gateway import SubmitJobRunGateway


def test_is_gateway() -> None:
    """SubmitJobRunGateway extends Gateway."""
    assert issubclass(SubmitJobRunGateway, Gateway)


def test_declares_submit() -> None:
    """SubmitJobRunGateway declares submit as an abstract method."""
    assert "submit" in SubmitJobRunGateway.__abstractmethods__
