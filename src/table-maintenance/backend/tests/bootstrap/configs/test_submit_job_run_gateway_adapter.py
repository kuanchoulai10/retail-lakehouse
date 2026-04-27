"""Tests for SubmitJobRunGatewayAdapter."""

from bootstrap.configs import SubmitJobRunGatewayAdapter


def test_members_have_correct_values() -> None:
    """Verify that SubmitJobRunGatewayAdapter members have correct string values."""
    assert SubmitJobRunGatewayAdapter.IN_MEMORY == "in_memory"
    assert SubmitJobRunGatewayAdapter.K8S == "k8s"


def test_members_are_strings() -> None:
    """Verify that SubmitJobRunGatewayAdapter members are str instances."""
    assert isinstance(SubmitJobRunGatewayAdapter.IN_MEMORY, str)
    assert isinstance(SubmitJobRunGatewayAdapter.K8S, str)
